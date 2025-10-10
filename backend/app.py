from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from services.db import Database
from pymysql.err import IntegrityError

app = Flask(__name__)
CORS(app)

DB = Database(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "appuser"),
    password=os.getenv("DB_PASSWORD", "app_password_here"),
    database=os.getenv("DB_NAME", "assim_saude")
)

# ----------------------------
# CARGOS
# ----------------------------
@app.route('/api/cargos', methods=['GET'])
def listar_cargos():
    nome = request.args.get('nome', '')
    cargos = DB.buscar_cargos_por_nome(nome)
    return jsonify(cargos), 200

@app.route('/api/cargos', methods=['POST'])
def adicionar_cargo():
    data = request.json or {}
    nome = data.get('nome')
    salario = data.get('salario')
    descricao = data.get('descricao', '')
    if not nome or salario is None:
        return jsonify({'erro': 'Nome e salário são obrigatórios.'}), 400
    novo_id = DB.inserir_cargo(nome, salario, descricao)
    return jsonify({'mensagem': 'Cargo criado', 'id': novo_id}), 201

@app.route('/api/cargos/<int:cargo_id>', methods=['PUT'])
def editar_cargo(cargo_id):
    data = request.json or {}
    updated = DB.atualizar_cargo(cargo_id, data.get('nome'), data.get('salario'), data.get('descricao'))
    if updated:
        return jsonify({'mensagem': 'Cargo atualizado'}), 200
    return jsonify({'erro': 'Cargo não encontrado'}), 404

@app.route('/api/cargos/<int:cargo_id>', methods=['DELETE'])
def remover_cargo(cargo_id):
    try:
        deleted = DB.deletar_cargo(cargo_id)
        if deleted:
            return jsonify({'mensagem': 'Cargo excluído'}), 200
        return jsonify({'erro': 'Cargo não encontrado'}), 404
    except IntegrityError:
        # FK: existem funcionários vinculados
        return jsonify({'erro': 'Não é possível excluir este cargo: existem funcionários vinculados.'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ----------------------------
# FUNCIONÁRIOS
# ----------------------------
@app.route('/api/funcionarios', methods=['GET'])
def listar_funcionarios():
    nome = request.args.get('nome', '')
    cpf = request.args.get('cpf', '')
    funcionarios = DB.buscar_funcionarios(nome, cpf)
    return jsonify(funcionarios), 200

@app.route('/api/funcionarios', methods=['POST'])
def adicionar_funcionario():
    data = request.json or {}
    required = ['nome', 'cpf', 'cargo_id']
    for f in required:
        if not data.get(f):
            return jsonify({'erro': f'Campo {f} é obrigatório'}), 400

    try:
        new_id = DB.inserir_funcionario(
            data.get('nome'),
            data.get('data_nascimento'),
            data.get('endereco'),
            data.get('cpf'),
            data.get('email'),
            data.get('telefone'),
            data.get('cargo_id')
        )
        return jsonify({'mensagem': 'Funcionário cadastrado', 'id': new_id}), 201
    except IntegrityError:
        return jsonify({'erro': 'CPF já cadastrado'}), 400
    except ValueError as ve:
        return jsonify({'erro': str(ve)}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/funcionarios/<int:func_id>', methods=['PUT'])
def editar_funcionario(func_id):
    data = request.json or {}
    try:
        updated = DB.atualizar_funcionario(func_id, data)
        if updated:
            return jsonify({'mensagem': 'Funcionário atualizado'}), 200
        return jsonify({'erro': 'Funcionário não encontrado'}), 404
    except ValueError as ve:
        return jsonify({'erro': str(ve)}), 400
    except IntegrityError:
        return jsonify({'erro': 'CPF já cadastrado'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/funcionarios/<int:func_id>', methods=['DELETE'])
def excluir_funcionario(func_id):
    try:
        deleted = DB.deletar_funcionario(func_id)
        if deleted:
            return jsonify({'mensagem': 'Funcionário excluído'}), 200
        return jsonify({'erro': 'Funcionário não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/counts', methods=['GET'])
def api_counts():
    """
    Retorna JSON com as contagens:
    { "cargos": N, "funcionarios": M, "relatorios": K or null }
    """
    try:
        cur = DB.conn.cursor()

        # cargos
        cur.execute("SELECT COUNT(*) as cnt FROM cargos")
        row = cur.fetchone()
        cargos = row['cnt'] if row and isinstance(row, dict) else (row[0] if row else 0)

        # funcionarios
        cur.execute("SELECT COUNT(*) as cnt FROM funcionarios")
        row = cur.fetchone()
        funcionarios = row['cnt'] if row and isinstance(row, dict) else (row[0] if row else 0)

        # verificar se existe tabela 'relatorios' no schema/config atual
        schema = os.getenv('DB_NAME', 'assim_saude')
        cur.execute("""SELECT COUNT(*) AS cnt FROM information_schema.tables
                       WHERE table_schema=%s AND table_name=%s""", (schema, 'relatorios'))
        row = cur.fetchone()
        exists = row['cnt'] if row and isinstance(row, dict) else (row[0] if row else 0)

        if exists:
            cur.execute("SELECT COUNT(*) as cnt FROM relatorios")
            row = cur.fetchone()
            relatorios = row['cnt'] if row and isinstance(row, dict) else (row[0] if row else 0)
        else:
            relatorios = None

        return jsonify({
            'cargos': cargos,
            'funcionarios': funcionarios,
            'relatorios': relatorios
        }), 200

    except Exception as e:
        # devolve erro em JSON para debugging
        return jsonify({'erro': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
