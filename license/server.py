# 密钥服务器
import base64
import sqlite3

import typer
from Cryptodome.Random import get_random_bytes
from flask import Flask, request, jsonify


def generate_key(client_id):
    key = base64.b64encode(get_random_bytes(32)).decode('utf-8')

    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO keys (client_id, key) VALUES (?, ?)", (client_id, key))
    conn.commit()
    conn.close()

    return key


def list_client_keys():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("SELECT * FROM keys")
    result = c.fetchall()
    conn.close()

    return result


class KeyServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.init_db()

        @self.app.route('/get_key', methods=['POST'])
        def get_key():
            client_id = request.json['client_id']

            conn = sqlite3.connect('keys.db')
            c = conn.cursor()
            c.execute("SELECT key FROM keys WHERE client_id = ?", (client_id,))
            result = c.fetchone()
            conn.close()

            if result:
                return jsonify({"key": result[0]})
            else:
                return jsonify({"error": "Key not found"}), 404

    def run(self, host):
        self.app.run(host)

    # 初始化数据库
    def init_db(self):
        conn = sqlite3.connect('keys.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keys (client_id TEXT PRIMARY KEY, key TEXT) ''')
        conn.commit()
        conn.close()


server_app = KeyServer()
typer_app = typer.Typer()


@typer_app.command()
def generate(client_id: str):
    key = generate_key(client_id)
    print(f"Generated key: {key}")


@typer_app.command()
def run(host: str = "0.0.0.0"):
    server_app.run(host)


@typer_app.command()
def list_keys():
    keys = list_client_keys()
    for client_id, key in keys:
        print(f"Client ID: {client_id}, Key: {key}")


if __name__ == '__main__':
    typer_app()
