class RevisionRepository:
    def __init__(self, connection):
        self.connection = connection

    def vigente(self, id_ruta):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, resultado, comentario, id_fiscalizador, fecha
                FROM validaciones_ruta WHERE id_ruta=%s AND vigente=1
                ORDER BY id DESC LIMIT 1
            """, (id_ruta,))
            return cursor.fetchone()

    def invalidar(self, id_ruta):
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE validaciones_ruta SET vigente=0 WHERE id_ruta=%s AND vigente=1", (id_ruta,))

    def registrar_conforme(self, id_ruta, id_fiscalizador, comentario):
        self.invalidar(id_ruta)
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO validaciones_ruta (id_ruta, resultado, comentario, id_fiscalizador, vigente)
                VALUES (%s, 'CONFORME', %s, %s, 1)
            """, (id_ruta, comentario, id_fiscalizador))
            return cursor.lastrowid
