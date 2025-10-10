import pymysql
import time
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError

class Database:
    def __init__(self, host, port, user, password, database, retries: int = 10, delay: int = 3):
        """
        Tenta conectar ao MySQL com retries. Se falhar depois de `retries`, levanta a exceção.
        """
        attempt = 0
        while True:
            try:
                self.conn = pymysql.connect(
                    host=host,
                    port=int(port),
                    user=user,
                    password=password,
                    database=database,
                    cursorclass=DictCursor,
                    autocommit=True
                )
                # Conectou com sucesso
                break
            except Exception as e:
                attempt += 1
                if attempt >= retries:
                    # não conseguiu depois de várias tentativas -> propaga erro (o Docker irá registrar no log)
                    raise
                print(f"[Database] Conexão falhou (tentativa {attempt}/{retries}): {e}. Re-tentando em {delay}s...")
                time.sleep(delay)

    # ----------------------------
    # CARGOS
    # ----------------------------
    def buscar_cargos_por_nome(self, nome=''):
        with self.conn.cursor() as cur:
            sql = "SELECT * FROM cargos WHERE nome LIKE %s ORDER BY id DESC"
            cur.execute(sql, (f"%{nome}%",))
            return cur.fetchall()

    def inserir_cargo(self, nome, salario, descricao):
        with self.conn.cursor() as cur:
            sql = "INSERT INTO cargos (nome, salario, descricao) VALUES (%s, %s, %s)"
            cur.execute(sql, (nome, salario, descricao))
            return cur.lastrowid

    def atualizar_cargo(self, cargo_id, nome, salario, descricao):
        with self.conn.cursor() as cur:
            sql = "UPDATE cargos SET nome=%s, salario=%s, descricao=%s WHERE id=%s"
            cur.execute(sql, (nome, salario, descricao, cargo_id))
            return cur.rowcount > 0

    def deletar_cargo(self, cargo_id):
        """
        Remove um cargo do banco de dados.
        Retorna True se foi deletado, False se não encontrado.
        Lança IntegrityError se existir funcionário vinculado.
        """
        try:
            with self.conn.cursor() as cursor:
                sql = "DELETE FROM cargos WHERE id = %s"
                linhas = cursor.execute(sql, (cargo_id,))
                self.conn.commit()
                return linhas > 0
        except Exception as e:
            self.conn.rollback()
            print("Erro ao deletar cargo:", e)
            raise


    # ----------------------------
    # FUNCIONARIOS
    # ----------------------------
    def buscar_funcionarios(self, nome='', cpf=''):
        with self.conn.cursor() as cur:
            sql = """SELECT f.*, c.nome AS cargo_nome, c.salario AS cargo_salario
                     FROM funcionarios f
                     JOIN cargos c ON f.cargo_id = c.id
                     WHERE f.nome LIKE %s AND f.cpf LIKE %s
                     ORDER BY f.id DESC"""
            cur.execute(sql, (f"%{nome}%", f"%{cpf}%"))
            return cur.fetchall()

    def inserir_funcionario(self, nome, data_nascimento, endereco, cpf, email, telefone, cargo_id):
        if not self.validar_cpf(cpf):
            raise ValueError("CPF inválido")
        with self.conn.cursor() as cur:
            sql = """INSERT INTO funcionarios
                     (nome, data_nascimento, endereco, cpf, email, telefone, cargo_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            try:
                cur.execute(sql, (nome, data_nascimento, endereco, cpf, email, telefone, cargo_id))
                return cur.lastrowid
            except IntegrityError as e:
                # Duplicate CPF => IntegrityError
                raise

    def atualizar_funcionario(self, func_id, data):
        # Se CPF for atualizado, valida
        cpf = data.get('cpf')
        if cpf and not self.validar_cpf(cpf):
            raise ValueError("CPF inválido")
        with self.conn.cursor() as cur:
            sql = """UPDATE funcionarios
                     SET nome=%s, data_nascimento=%s, endereco=%s, cpf=%s, email=%s, telefone=%s, cargo_id=%s
                     WHERE id=%s"""
            cur.execute(sql, (
                data.get('nome'),
                data.get('data_nascimento'),
                data.get('endereco'),
                data.get('cpf'),
                data.get('email'),
                data.get('telefone'),
                data.get('cargo_id'),
                func_id
            ))
            return cur.rowcount > 0

    def deletar_funcionario(self, func_id):
        with self.conn.cursor() as cur:
            sql = "DELETE FROM funcionarios WHERE id=%s"
            cur.execute(sql, (func_id,))
            return cur.rowcount > 0

    # ----------------------------
    # VALIDAÇÃO DE CPF
    # ----------------------------
    def validar_cpf(self, cpf: str) -> bool:
        if not cpf:
            return False
        cpf = ''.join(filter(str.isdigit, str(cpf)))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False

        def calc_digito(cpf, peso):
            soma = 0
            for i in range(peso - 1):
                soma += int(cpf[i]) * (peso - i)
            resto = (soma * 10) % 11
            return resto if resto < 10 else 0

        try:
            return (calc_digito(cpf, 10) == int(cpf[9]) and
                    calc_digito(cpf, 11) == int(cpf[10]))
        except Exception:
            return False
