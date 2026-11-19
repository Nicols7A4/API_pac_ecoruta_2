/**
 * EcoRuta · Consola de Supervisión Web
 * Reto R5 / SU-16: Dashboard, Monitoreo en Mapa, Control de Rutas e Incidencias en Tiempo Real
 */

const state = {
  token: localStorage.getItem('ecorutaToken') || '',
  user: JSON.parse(localStorage.getItem('ecorutaUser') || 'null'),
  activeTab: 'dashboard',
  selectedRouteId: Number(localStorage.getItem('ecorutaSelectedRoute')) || 0,
  routes: [],
  summary: null,
  allPoints: [],
  allIncidents: [],
  map: null,
  miniMap: null,
  mapMarkers: null,
  miniMapMarkers: null,
  timer: null,
  isRefreshing: false,
  autoRefreshInterval: 20000 // 20 segundos
};

// ================= UTILIDADES =================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (m) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

function formatDate(isoStr) {
  if (!isoStr) return 'N/A';
  try {
    const d = new Date(isoStr);
    return isNaN(d) ? isoStr : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

function formatDateTime(isoStr) {
  if (!isoStr) return 'Fecha no disponible';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return String(isoStr);
    return d.toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return String(isoStr);
  }
}

function getIncidentEvidenceUrl(inc) {
  const evidence = Array.isArray(inc.evidencias) ? inc.evidencias[0] : null;
  const raw = evidence?.url || evidence?.ruta_archivo || inc.foto_url ||
    inc.foto_evidencia || inc.evidencia || '';
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  const path = String(raw).replace(/\\/g, '/');
  if (path.startsWith('/')) return path;
  if (path.startsWith('uploads/')) return '/' + path;
  return '/uploads/incidencias/' + path;
}

// ================= COMUNICACIÓN CON API REST =================
async function api(path, options = {}) {
  const url = '/api/' + path;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  if (state.token) {
    headers['Authorization'] = 'Bearer ' + state.token;
  }

  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new Error('Error de conexión con el servidor backend');
  }

  let body = {};
  try {
    body = await response.json();
  } catch {}

  if (response.status === 401) {
    logout();
    throw new Error('Sesión expirada o credenciales inválidas');
  }

  if (!response.ok || body.status === false) {
    throw new Error(body.message || `Error del servidor HTTP ${response.status}`);
  }

  return body.data;
}

// ================= AUTENTICACIÓN =================
function checkSession() {
  // Eliminar remanente de HTML antiguo si existiese en caché de Safari
  const oldLogin = document.getElementById('login');
  if (oldLogin) oldLogin.remove();

  const isAuth = Boolean(state.token && state.user && state.user.rol === 'SUPERVISOR');
  const loginView = $('#loginView');
  const appView = $('#appView');

  if (loginView) {
    loginView.hidden = isAuth;
    loginView.style.display = isAuth ? 'none' : 'grid';
  }
  if (appView) {
    appView.hidden = !isAuth;
    appView.style.display = isAuth ? 'block' : 'none';
  }

  if (isAuth) {
    const userName = $('#userName');
    const userInitial = $('#userInitial');
    if (userName) userName.textContent = state.user.nombre || 'Supervisor';
    if (userInitial) userInitial.textContent = (state.user.nombre || 'S').charAt(0).toUpperCase();
    startApp();
  } else {
    stopApp();
  }
}

function logout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('ecorutaToken');
  localStorage.removeItem('ecorutaUser');
  localStorage.removeItem('ecorutaSelectedRoute');
  checkSession();
}

$('#loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = $('#loginError');
  errorEl.hidden = true;
  errorEl.textContent = '';

  const submitBtn = $('#btnLoginSubmit');
  submitBtn.disabled = true;

  try {
    const data = await api('auth/login', {
      method: 'POST',
      body: JSON.stringify({
        correo: $('#correo').value.trim(),
        password: $('#password').value
      })
    });

    if (data.usuario.rol !== 'SUPERVISOR') {
      throw new Error('Acceso restringido: Se requiere una cuenta con rol SUPERVISOR');
    }

    state.token = data.token;
    state.user = data.usuario;
    localStorage.setItem('ecorutaToken', state.token);
    localStorage.setItem('ecorutaUser', JSON.stringify(state.user));
    checkSession();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
});

// Autocompletar Demo
$('#btnFillDemo').addEventListener('click', () => {
  $('#correo').value = 'supervisor@ecoruta.pe';
  $('#password').value = 'Supervisor123';
  $('#loginError').hidden = true;
  $('#btnLoginSubmit').focus();
});

// Toggle Ver Contraseña
$('#togglePasswordBtn').addEventListener('click', () => {
  const pwInput = $('#password');
  const isPw = pwInput.type === 'password';
  pwInput.type = isPw ? 'text' : 'password';
});

$('#btnLogout').addEventListener('click', logout);

// ================= INICIALIZACIÓN DE LA APP =================
function startApp() {
  // Configurar fecha de hoy en el filtro
  const today = new Date().toISOString().slice(0, 10);
  if (!$('#filtroFecha').value) {
    $('#filtroFecha').value = today;
  }

  // Event Listeners de Filtros
  $('#filtroFecha').addEventListener('change', () => refreshData(true));
  $('#filtroEstado').addEventListener('change', () => filterAndRender());
  $('#filtroBuscar').addEventListener('input', () => filterAndRender());
  $('#btnVerTodasFechas').addEventListener('click', () => {
    $('#filtroFecha').value = '';
    $('#filtroEstado').value = '';
    $('#filtroBuscar').value = '';
    refreshData(true);
  });

  // Botón de refresco manual
  $('#btnRefresh').addEventListener('click', () => refreshData(true));

  // Pestañas
  $$('.nav-tab').forEach((tabBtn) => {
    tabBtn.addEventListener('click', () => {
      setTab(tabBtn.dataset.tab);
    });
  });

  // Selector de ruta en mapa
  $('#mapRutaSelect').addEventListener('change', (e) => {
    renderMapMarkers(Number(e.target.value));
  });

  $('#btnRecenterMap').addEventListener('click', () => {
    if (state.map && state.mapMarkers) {
      const bounds = state.mapMarkers.getBounds();
      if (bounds.isValid()) {
        state.map.fitBounds(bounds, { padding: [40, 40] });
      } else {
        state.map.setView([-6.77143, -79.83877], 14);
      }
    }
  });

  // Pestañas secundarias en detalle de ruta
  $$('.insp-subtab').forEach((st) => {
    st.addEventListener('click', () => {
      $$('.insp-subtab').forEach((b) => b.classList.remove('active'));
      $$('.subtab-pane').forEach((p) => p.classList.remove('active'));
      st.classList.add('active');
      $(`#inspSubtab${st.dataset.subtab.charAt(0).toUpperCase() + st.dataset.subtab.slice(1)}`).classList.add('active');
    });
  });

  // Filtros de incidencias
  $$('.filter-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
      $$('.filter-pill').forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      renderIncidents(pill.dataset.incFilter);
    });
  });

  // Formulario Gestionar Incidencia
  $('#formGestionarIncidencia').addEventListener('submit', handleGuardarIncidencia);

  // Botón Ver en Mapa desde inspector
  $('#btnVerEnMapaRuta').addEventListener('click', () => {
    if (state.selectedRouteId) {
      setTab('mapa');
      $('#mapRutaSelect').value = state.selectedRouteId;
      renderMapMarkers(state.selectedRouteId);
    }
  });

  // Botón Historial desde inspector
  $('#btnHistorialRuta').addEventListener('click', async () => {
    if (state.selectedRouteId) {
      await showHistorialModal(state.selectedRouteId);
    }
  });

  // Iniciar Maps
  initMaps();

  // Carga inicial
  refreshData(true);

  // Auto-refresco en segundo plano usando setInterval
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(() => {
    if (!document.hidden) {
      refreshData(false);
    }
  }, state.autoRefreshInterval);

  // Refrescar al volver a la pestaña del navegador
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      refreshData(false);
    }
  });
}

function stopApp() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
}

function setTab(tabName) {
  state.activeTab = tabName;
  $$('.nav-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === tabName));
  $$('.tab-pane').forEach((p) => p.classList.toggle('active', p.id === 'tab-' + tabName));

  if (tabName === 'mapa' && state.map) {
    setTimeout(() => {
      state.map.invalidateSize();
      if (state.mapMarkers && state.mapMarkers.getBounds().isValid()) {
        state.map.fitBounds(state.mapMarkers.getBounds(), { padding: [40, 40] });
      }
    }, 150);
  }
}

// ================= MAPAS LEAFLET =================
function initMaps() {
  if (!window.L) return;

  // Mapa Principal
  if (!state.map) {
    state.map = L.map('fullMap', { zoomControl: true }).setView([-6.77143, -79.83877], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors · EcoRuta'
    }).addTo(state.map);
    state.mapMarkers = L.featureGroup().addTo(state.map);
  }

  // Mini Mapa del Inspector
  if (!state.miniMap) {
    state.miniMap = L.map('inspectorMiniMap', { zoomControl: false, attributionControl: false }).setView([-6.77143, -79.83877], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(state.miniMap);
    state.miniMapMarkers = L.featureGroup().addTo(state.miniMap);
  }
}

// ================= OBTENCIÓN Y SINCRONIZACIÓN DE DATOS =================
async function refreshData(showIndicator = true) {
  if (state.isRefreshing) return;
  state.isRefreshing = true;

  if (showIndicator) {
    $('#btnRefresh').classList.add('spinning');
    $('#syncTimestamp').textContent = 'Actualizando datos...';
  }

  try {
    const fecha = $('#filtroFecha').value;
    const queryParams = new URLSearchParams();
    if (fecha) queryParams.set('fecha', fecha);

    // 1. Resumen de Supervisión
    // Sin fecha, el listado muestra todas las rutas; el resumen debe usar el
    // mismo alcance para que los KPI no se queden limitados al día actual.
    const resumenUrl = fecha
      ? 'supervision/resumen?fecha=' + fecha
      : 'supervision/resumen?fecha_inicio=2000-01-01&fecha_fin=2100-12-31';
    const rutasUrl = 'rutas' + (queryParams.toString() ? '?' + queryParams.toString() : '');

    const [resumenData, rutasData, puntosData] = await Promise.all([
      api(resumenUrl).catch(() => null),
      api(rutasUrl).catch(() => ({ rutas: [] })),
      api('puntos').catch(() => [])
    ]);

    state.summary = resumenData;
    state.routes = rutasData.rutas || [];
    state.allPoints = puntosData.puntos || puntosData || [];

    // Recolectar incidencias de las rutas actuales
    await fetchIncidentsForCurrentRoutes();

    // Renderizar Vistas
    renderDashboard();
    filterAndRender();
    updateMapRouteOptions();
    renderMapMarkers(Number($('#mapRutaSelect').value) || 0);

    const now = new Date();
    $('#syncTimestamp').textContent = 'Sincronizado: ' + now.toLocaleTimeString();
  } catch (err) {
    $('#syncTimestamp').textContent = 'Aviso: ' + err.message;
  } finally {
    state.isRefreshing = false;
    $('#btnRefresh').classList.remove('spinning');
  }
}

async function fetchIncidentsForCurrentRoutes() {
  const incidentsList = [];
  const routePromises = state.routes.slice(0, 15).map(async (r) => {
    try {
      const data = await api(`rutas/${r.id}/incidencias`);
      if (data && data.incidencias) {
        data.incidencias.forEach((inc) => {
          inc.ruta_codigo = r.codigo;
          inc.ruta_id = r.id;
          incidentsList.push(inc);
        });
      }
    } catch {}
  });

  await Promise.all(routePromises);
  state.allIncidents = incidentsList;

  // Actualizar contador en pestaña de incidencias
  const abiertasCount = incidentsList.filter((i) => i.estado === 'ABIERTA' || i.estado === 'EN_REVISION').length;
  const pill = $('#incidenciasPill');
  if (abiertasCount > 0) {
    pill.hidden = false;
    pill.textContent = abiertasCount;
  } else {
    pill.hidden = true;
  }

  renderIncidents();
}

// ================= RENDERIZADO: TAB 1 (DASHBOARD) =================
function renderDashboard() {
  const r = state.summary;
  if (!r) return;

  const totalRutas = r.rutas?.total ?? state.routes.length;
  const rutasEnCurso = r.rutas?.en_curso ?? state.routes.filter((x) => x.estado === 'EN_CURSO').length;
  const puntosAtendidos = (r.puntos?.atendidos ?? 0) + (r.puntos?.con_incidencia ?? 0);
  const totalPuntos = r.puntos?.total ?? 0;
  const porcentajeAvance = r.avance_general_porcentaje ?? (totalPuntos ? Math.round((puntosAtendidos / totalPuntos) * 100) : 0);
  const puntosPendientes = r.puntos?.pendientes ?? Math.max(0, totalPuntos - puntosAtendidos);
  const incAbiertas = r.incidencias?.abiertas ?? 0;
  const incCriticas = r.incidencias?.criticas ?? 0;

  // Actualizar KPIs
  $('#kpiRutasTotal').textContent = totalRutas;
  $('#kpiRutasEnCurso').textContent = `${rutasEnCurso} activas ahora`;
  $('#kpiPuntosAtendidos').textContent = puntosAtendidos;
  $('#kpiPuntosPorcentaje').textContent = `${porcentajeAvance}% completado`;
  $('#kpiPuntosPendientes').textContent = puntosPendientes;
  $('#kpiIncidenciasAbiertas').textContent = incAbiertas;
  $('#kpiIncidenciasCriticas').textContent = `${incCriticas} críticas`;

  // Barra de Cumplimiento
  $('#dashboardAvancePorcentaje').textContent = `${porcentajeAvance}%`;
  $('#dashboardAvanceBar').style.width = `${Math.min(100, porcentajeAvance)}%`;

  // Chips de Estados
  $('#chipProgramadas').textContent = r.rutas?.programadas ?? state.routes.filter((x) => x.estado === 'PROGRAMADA').length;
  $('#chipEnCurso').textContent = rutasEnCurso;
  $('#chipFinalizadas').textContent = r.rutas?.finalizadas ?? state.routes.filter((x) => x.estado === 'FINALIZADA').length;
  $('#chipObservadas').textContent = r.rutas?.observadas ?? state.routes.filter((x) => x.estado === 'OBSERVADA').length;

  // Fiscalización
  const fis = r.fiscalizacion || {};
  $('#fiscalizacionTexto').textContent = `${fis.pendientes_revision ?? 0} listas para revisión · ${fis.conformes ?? 0} conformes · ${fis.observadas ?? 0} observadas`;

  // Rutas en operación en Dashboard
  const dashList = $('#dashboardRutasList');
  const activeRoutes = state.routes.filter((x) => x.estado === 'EN_CURSO' || x.estado === 'PROGRAMADA').slice(0, 5);

  if (activeRoutes.length === 0) {
    dashList.innerHTML = '<p style="color:var(--color-text-muted); text-align:center; padding:24px;">No hay rutas activas en este momento.</p>';
  } else {
    dashList.innerHTML = activeRoutes.map((route) => `
      <div class="dash-route-card" onclick="app.selectRouteAndOpen(${route.id})">
        <div class="dash-route-top">
          <div>
            <span class="dash-route-code">${escapeHtml(route.codigo)}</span>
            <div class="dash-route-sub">${escapeHtml(route.operario?.nombre || 'Sin operario')} · ${escapeHtml(route.vehiculo?.placa || 'Sin camión')}</div>
          </div>
          <span class="badge ${route.estado}">${route.estado}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${Math.round(route.avance_porcentaje || 0)}%"></div>
        </div>
      </div>
    `).join('');
  }
}

// ================= RENDERIZADO: TAB 3 (CONTROL DE RUTAS) =================
function filterAndRender() {
  const estado = $('#filtroEstado').value;
  const query = $('#filtroBuscar').value.trim().toLowerCase();

  let filtered = state.routes;

  if (estado) {
    filtered = filtered.filter((r) => r.estado === estado);
  }

  if (query) {
    filtered = filtered.filter((r) =>
      (r.codigo || '').toLowerCase().includes(query) ||
      (r.operario?.nombre || '').toLowerCase().includes(query) ||
      (r.vehiculo?.placa || '').toLowerCase().includes(query)
    );
  }

  $('#routesCountBadge').textContent = filtered.length;

  const container = $('#rutasContainer');
  if (filtered.length === 0) {
    container.innerHTML = '<p style="color:var(--color-text-muted); text-align:center; padding:32px;">No se encontraron rutas con los filtros aplicados.</p>';
    return;
  }

  container.innerHTML = filtered.map((r) => {
    const isSelected = r.id === state.selectedRouteId;
    return `
      <div class="route-item-card ${isSelected ? 'selected' : ''}" onclick="app.selectRoute(${r.id})">
        <div class="route-item-header">
          <span class="route-item-code">${escapeHtml(r.codigo)}</span>
          <span class="badge ${r.estado}">${r.estado}</span>
        </div>
        <div class="route-item-meta">
          ${escapeHtml(r.fecha)} · Turno ${escapeHtml(r.turno)}<br>
          ${escapeHtml(r.operario?.nombre || 'Sin operario')} · ${escapeHtml(r.vehiculo?.placa || 'Sin placa')}
        </div>
        <div class="route-item-progress">
          <div class="progress-track">
            <div class="progress-fill" style="width: ${Math.round(r.avance_porcentaje || 0)}%"></div>
          </div>
          <span>${Math.round(r.avance_porcentaje || 0)}%</span>
        </div>
      </div>
    `;
  }).join('');

  // Si hay una seleccionada, renderizar su detalle
  if (state.selectedRouteId && filtered.some((r) => r.id === state.selectedRouteId)) {
    loadRouteDetail(state.selectedRouteId);
  } else if (filtered.length > 0 && !state.selectedRouteId) {
    selectRoute(filtered[0].id);
  } else if (filtered.length === 0) {
    $('#inspectorEmpty').hidden = false;
    $('#inspectorContent').hidden = true;
  }
}

async function selectRoute(id) {
  state.selectedRouteId = id;
  localStorage.setItem('ecorutaSelectedRoute', id);

  // Marcar visualmente
  $$('.route-item-card').forEach((el) => {
    el.classList.remove('selected');
  });

  await loadRouteDetail(id);
}

function selectRouteAndOpen(id) {
  setTab('rutas');
  selectRoute(id);
}

async function loadRouteDetail(id) {
  $('#inspectorEmpty').hidden = true;
  $('#inspectorContent').hidden = false;

  try {
    const [detailData, pointsData, incidentsData] = await Promise.all([
      api(`rutas/${id}`),
      api(`rutas/${id}/puntos`),
      api(`rutas/${id}/incidencias`).catch(() => ({ incidencias: [] }))
    ]);

    const r = detailData.ruta || detailData;
    const points = pointsData.puntos || pointsData || [];
    const incidents = incidentsData.incidencias || [];

    // Cabecera
    $('#inspCodigo').textContent = r.codigo;
    $('#inspEstadoBadge').textContent = r.estado;
    $('#inspEstadoBadge').className = `badge ${r.estado}`;
    $('#inspMetaInfo').textContent = `${r.fecha} · Turno ${r.turno} · Total ${points.length} puntos programados`;

    // Grilla
    $('#inspOperarioNombre').textContent = r.operario?.nombre || 'Sin operario asignado';
    $('#inspVehiculoPlaca').textContent = r.vehiculo ? `${r.vehiculo.placa} (${r.vehiculo.tipo})` : 'Sin vehículo';
    $('#inspAvanceText').textContent = `${Math.round(r.avance_porcentaje || 0)}%`;
    const atendidosCount = points.filter((p) => p.estado === 'ATENDIDO' || p.estado === 'CON_INCIDENCIA').length;
    $('#inspPuntosConteo').textContent = `${atendidosCount} / ${points.length}`;

    // Subtabs conteos
    $('#countSubtabPuntos').textContent = points.length;
    $('#countSubtabIncidencias').textContent = incidents.length;

    // Timeline de Puntos
    renderTimelinePoints(points);

    // Lista de Incidencias de la Ruta
    renderRouteIncidents(incidents);

    // Mini Mapa
    renderMiniMap(points);
  } catch (err) {
    console.error('Error cargando detalle de ruta:', err);
  }
}

function renderTimelinePoints(points) {
  const container = $('#inspPuntosTimeline');
  if (points.length === 0) {
    container.innerHTML = '<p style="color:var(--color-text-muted); text-align:center; padding:16px;">Esta ruta no tiene puntos registrados.</p>';
    return;
  }

  container.innerHTML = points.map((p, idx) => `
    <div class="timeline-step">
      <div class="step-left">
        <span class="step-order">${p.orden || (idx + 1)}</span>
        <div class="step-info">
          <strong>${escapeHtml(p.punto?.nombre || 'Punto #' + p.id)}</strong>
          <span>${escapeHtml(p.punto?.direccion || 'Chiclayo')} · QR: ${escapeHtml(p.punto?.codigo_qr || 'N/A')}${p.fecha_atencion ? ' · Atendido: ' + formatDate(p.fecha_atencion) : ''}</span>
        </div>
      </div>
      <span class="step-status-pill ${p.estado}">${p.estado}</span>
    </div>
  `).join('');
}

function renderRouteIncidents(incidents) {
  const container = $('#inspIncidenciasList');
  if (incidents.length === 0) {
    container.innerHTML = '<p style="color:var(--color-text-muted); text-align:center; padding:20px;">No hay incidencias reportadas en esta ruta.</p>';
    return;
  }

  container.innerHTML = incidents.map((i) => `
    <div class="incident-card">
      <div class="incident-card-top">
        <span class="incident-type">${escapeHtml(i.tipo)}</span>
        <span class="badge ${i.estado}">${i.estado}</span>
      </div>
      <p class="incident-desc">${escapeHtml(i.descripcion)}</p>
      <div class="incident-meta-box">
        <span>Reportado por: <b>${escapeHtml(i.usuario?.nombre || 'Operario')}</b></span>
        <span>Fecha: ${formatDate(i.fecha_hora || i.fecha)}</span>
      </div>
    </div>
  `).join('');
}

function renderMiniMap(points) {
  if (!state.miniMap || !window.L) return;

  state.miniMapMarkers.clearLayers();
  const bounds = [];

  points.forEach((p) => {
    if (p.punto?.latitud && p.punto?.longitud) {
      const lat = p.punto.latitud;
      const lng = p.punto.longitud;
      bounds.push([lat, lng]);

      const color = p.estado === 'ATENDIDO' ? '#059669' : p.estado === 'CON_INCIDENCIA' ? '#f59e0b' : '#ef4444';
      L.circleMarker([lat, lng], {
        radius: 7,
        color,
        fillColor: color,
        fillOpacity: 0.9,
        weight: 2
      }).addTo(state.miniMapMarkers);
    }
  });

  setTimeout(() => {
    state.miniMap.invalidateSize();
    if (bounds.length > 0) {
      state.miniMap.fitBounds(bounds, { padding: [20, 20] });
    }
  }, 100);
}

// ================= RENDERIZADO: TAB 2 (MAPA PRINCIPAL) =================
function updateMapRouteOptions() {
  const sel = $('#mapRutaSelect');
  const currentVal = sel.value;
  sel.innerHTML = '<option value="0">Ver Todas las Rutas y Puntos</option>' +
    state.routes.map((r) => `<option value="${r.id}">${escapeHtml(r.codigo)} (${r.estado} · ${r.fecha})</option>`).join('');
  if (currentVal) sel.value = currentVal;
}

function renderMapMarkers(filterRouteId = 0) {
  if (!state.map || !window.L) return;

  state.mapMarkers.clearLayers();
  const bounds = [];

  // Puntos a mostrar
  let pointsToShow = [];

  if (filterRouteId > 0) {
    // Buscar puntos de la ruta seleccionada
    const r = state.routes.find((x) => x.id === filterRouteId);
    if (r) {
      api(`rutas/${filterRouteId}/puntos`).then((data) => {
        const pts = data.puntos || data || [];
        pts.forEach((pt) => {
          if (pt.punto?.latitud && pt.punto?.longitud) {
            addMarkerToMap(pt.punto.latitud, pt.punto.longitud, pt.punto.nombre, pt.estado, pt.punto.codigo_qr, pt.fecha_atencion, r.codigo);
            bounds.push([pt.punto.latitud, pt.punto.longitud]);
          }
        });
        if (bounds.length > 0) {
          state.map.fitBounds(bounds, { padding: [50, 50] });
        }
      });
      return;
    }
  }

  // Si es 0: mostramos todos los puntos base de la ciudad
  state.allPoints.forEach((p) => {
    if (p.latitud && p.longitud) {
      addMarkerToMap(p.latitud, p.longitud, p.nombre, 'PENDIENTE', p.codigo_qr, null, 'Punto Ciudad');
      bounds.push([p.latitud, p.longitud]);
    }
  });

  if (bounds.length > 0) {
    state.map.fitBounds(bounds, { padding: [50, 50] });
  }
}

function addMarkerToMap(lat, lng, name, status, qr, date, routeCode) {
  const color = status === 'ATENDIDO' ? '#059669' : status === 'CON_INCIDENCIA' ? '#f59e0b' : '#ef4444';

  const marker = L.circleMarker([lat, lng], {
    radius: 9,
    color: '#ffffff',
    fillColor: color,
    fillOpacity: 0.95,
    weight: 2
  });

  const popupHtml = `
    <div style="font-family:Inter,sans-serif; min-width:180px;">
      <strong style="font-size:13px; color:#0f172a;">${escapeHtml(name)}</strong><br>
      <span style="font-size:11px; color:#64748b;">QR: ${escapeHtml(qr)} · ${escapeHtml(routeCode)}</span>
      <div style="margin-top:6px; display:flex; align-items:center; justify-content:space-between;">
        <span class="badge ${status}" style="font-size:10px;">${status}</span>
        ${date ? `<span style="font-size:10px; color:#64748b;">${formatDate(date)}</span>` : ''}
      </div>
    </div>
  `;

  marker.bindPopup(popupHtml).addTo(state.mapMarkers);
}

// ================= RENDERIZADO: TAB 4 (INCIDENCIAS) =================
function renderIncidents(statusFilter = 'TODAS') {
  const container = $('#incidenciasGrid');
  let list = state.allIncidents;

  if (statusFilter !== 'TODAS') {
    list = list.filter((i) => i.estado === statusFilter);
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding:48px; color:var(--color-text-muted);">
        <p style="font-size:1.1rem; font-weight:600;">No hay incidencias que coincidan con este filtro.</p>
        <p style="font-size:0.85rem; margin-top:4px;">Todas las operaciones se encuentran en estado óptimo.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map((inc) => {
    const isCritica = inc.es_critica || inc.tipo === 'CONTENEDOR_DANADO' || inc.tipo === 'ZONA_INACCESIBLE';
    const fotoUrl = getIncidentEvidenceUrl(inc);
    const fechaIncidencia = inc.fecha_registro || inc.fecha_captura || inc.fecha_hora ||
      inc.fecha_creacion || inc.fecha;
    const caption = `${inc.tipo || 'Incidencia'} - ${inc.descripcion || 'Evidencia fotográfica'}`;

    return `
      <div class="incident-card">
        <div class="incident-card-top">
          <div>
            <span class="incident-type">${escapeHtml(inc.tipo)}</span>
            <div style="font-size:0.78rem; color:var(--color-text-muted); margin-top:2px;">
              Ruta: <b>${escapeHtml(inc.ruta_codigo || 'N/A')}</b> · Incidencia #${inc.id}
            </div>
          </div>
          ${isCritica ? '<span class="badge-critica">CRÍTICA</span>' : `<span class="badge ${inc.estado}">${inc.estado}</span>`}
        </div>

        <p class="incident-desc">${escapeHtml(inc.descripcion)}</p>

        ${fotoUrl ? `
          <div class="incident-thumb-row incident-evidence" data-evidence-state="available">
            <img class="incident-img-thumb"
                 src="${escapeHtml(fotoUrl)}"
                 alt="Evidencia fotográfica de ${escapeHtml(inc.tipo)}"
                 data-src="${escapeHtml(fotoUrl)}"
                 data-caption="${escapeHtml(caption)}"
                 onclick="app.openEvidence(this)"
                 onerror="app.handleEvidenceError(this)">
            <span class="incident-evidence-label">Clic en la imagen para ampliarla</span>
          </div>
        ` : `
          <div class="incident-thumb-row incident-evidence is-unavailable">
            <div class="incident-img-placeholder" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
            </div>
            <span class="incident-evidence-label">Sin evidencia fotográfica registrada</span>
          </div>
        `}

        <div class="incident-meta-box">
          <span>Reportó: <b>${escapeHtml(inc.usuario?.nombre || 'Operario')}</b></span>
          <span>Fecha: <b>${escapeHtml(formatDateTime(fechaIncidencia))}</b></span>
          ${inc.observacion_control ? `<span style="color:var(--color-primary-dark);"><b>Resolución:</b> ${escapeHtml(inc.observacion_control)}</span>` : ''}
        </div>

        <div class="incident-card-actions">
          <span class="badge ${inc.estado}">${inc.estado}</span>
          ${inc.estado !== 'RESUELTA' ? `
            <button class="btn-secondary" onclick="app.openGestionarModal(${inc.id}, '${escapeHtml(inc.tipo)}', '${inc.estado}')">
              <span>Gestionar / Resolver</span>
            </button>
          ` : '<span style="font-size:0.8rem; color:var(--color-primary); font-weight:700;">✓ Resuelta</span>'}
        </div>
      </div>
    `;
  }).join('');
}

// ================= GESTIONAR INCIDENCIA (SU-08) =================
function openGestionarModal(id, tipo, estadoActual) {
  $('#modalIncId').value = id;
  $('#modalIncTitulo').textContent = `Gestionar Incidencia #${id} (${tipo})`;
  $('#modalIncEstado').value = estadoActual === 'EN_REVISION' ? 'RESUELTA' : 'EN_REVISION';
  $('#modalIncComentario').value = '';
  $('#modalGestionarIncidencia').hidden = false;
}

async function handleGuardarIncidencia(e) {
  e.preventDefault();
  const id = $('#modalIncId').value;
  const nuevoEstado = $('#modalIncEstado').value;
  const observacion = $('#modalIncComentario').value.trim();

  try {
    await api(`incidencias/${id}/estado`, {
      method: 'PUT',
      body: JSON.stringify({
        estado: nuevoEstado,
        observacion: observacion
      })
    });

    closeModal('modalGestionarIncidencia');
    await refreshData(true);
  } catch (err) {
    alert('Error al actualizar incidencia: ' + err.message);
  }
}

// ================= HISTORIAL DE AUDITORÍA =================
async function showHistorialModal(rutaId) {
  $('#modalHistTitulo').textContent = `Historial de Ruta #${rutaId}`;
  const body = $('#modalHistorialBody');
  body.innerHTML = '<p style="text-align:center; padding:20px;">Cargando historial...</p>';
  $('#modalHistorial').hidden = false;

  try {
    const data = await api(`rutas/${rutaId}/historial`);
    const logs = data.historial || [];

    if (logs.length === 0) {
      body.innerHTML = '<p style="text-align:center; padding:20px; color:var(--color-text-muted);">No hay registros de auditoría para esta ruta.</p>';
      return;
    }

    body.innerHTML = logs.map((log) => `
      <div class="history-entry">
        <div class="history-dot"></div>
        <div class="history-content">
          <strong>Transición: ${escapeHtml(log.estado_anterior || 'INICIAL')} → ${escapeHtml(log.estado_nuevo)}</strong>
          <small>${formatDate(log.fecha_cambio || log.created_at)} · Por ${escapeHtml(log.usuario?.nombre || 'Sistema')} (${escapeHtml(log.usuario?.rol || 'SUPERVISOR')})</small>
          ${log.comentario ? `<div class="history-comment">${escapeHtml(log.comentario)}</div>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    body.innerHTML = `<p style="color:var(--state-critica); text-align:center;">Error: ${err.message}</p>`;
  }
}

// ================= MODALES Y LIGHTBOX =================
function closeModal(modalId) {
  $(`#${modalId}`).hidden = true;
}

function openLightbox(src, caption) {
  $('#lightboxImg').src = src;
  $('#lightboxCaption').textContent = caption || '';
  $('#modalLightbox').hidden = false;
}

function openEvidence(img) {
  if (!img?.dataset?.src) return;
  openLightbox(img.dataset.src, img.dataset.caption || 'Evidencia fotográfica');
}

function handleEvidenceError(img) {
  const row = img?.closest('.incident-evidence');
  if (!row) return;
  img.hidden = true;
  row.dataset.evidenceState = 'missing';
  row.classList.add('is-unavailable');
  if (!row.querySelector('.incident-img-placeholder')) {
    const placeholder = document.createElement('div');
    placeholder.className = 'incident-img-placeholder';
    placeholder.setAttribute('aria-hidden', 'true');
    placeholder.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="m3 3 18 18"/><path d="m21 15-5-5-2 2"/></svg>';
    row.insertBefore(placeholder, row.firstChild);
  }
  const label = row.querySelector('.incident-evidence-label');
  if (label) label.textContent = 'Imagen no disponible en el servidor';
}

function closeLightbox() {
  $('#modalLightbox').hidden = true;
}

// Exportar funciones a window para eventos inline
window.app = {
  setTab,
  selectRoute,
  selectRouteAndOpen,
  openGestionarModal,
  closeModal,
  openLightbox,
  openEvidence,
  handleEvidenceError,
  closeLightbox
};

// Iniciar chequeo de sesión al cargar DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', checkSession);
} else {
  checkSession();
}
