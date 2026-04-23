"""Inline source for eval fixtures.

Kept in code (not 60 separate file writes) so the corpus is easy to grow and
review. `ensure_fixtures()` writes each entry to disk on first use so that the
pipeline sees real files, matching what the runtime does.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@dataclass(frozen=True)
class Fixture:
    relpath: str
    language: str
    content: str
    # Critical-severity categories the model SHOULD flag on this file.
    # Empty for clean fixtures.
    expected_criticals: tuple[str, ...] = ()


# Each buggy fixture plants one clear critical-severity issue.
# Categories loosely match the SYSTEM_RULES taxonomy.
BUGGY: list[Fixture] = [
    Fixture(
        "buggy/sql_injection_fstring.py",
        "python",
        """\
import sqlite3
def find_user(conn, name):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cur.fetchall()
""",
        ("sql_injection",),
    ),
    Fixture(
        "buggy/sql_injection_concat.py",
        "python",
        """\
def get_order(conn, order_id):
    q = "SELECT * FROM orders WHERE id = " + str(order_id)
    return conn.execute(q).fetchone()
""",
        ("sql_injection",),
    ),
    Fixture(
        "buggy/sql_injection_format.py",
        "python",
        """\
def find_by_email(conn, email):
    return conn.execute("SELECT id FROM users WHERE email = '{}'".format(email)).fetchall()
""",
        ("sql_injection",),
    ),
    Fixture(
        "buggy/hardcoded_api_key.py",
        "python",
        """\
import requests
API_KEY = "sk-proj-9f2e4a1b8c7d6e5f4a3b2c1d0e9f8a7b"
def call():
    return requests.get("https://api.example.com/v1/me", headers={"Authorization": f"Bearer {API_KEY}"})
""",
        ("hardcoded_secret",),
    ),
    Fixture(
        "buggy/hardcoded_password.py",
        "python",
        """\
DB_PASSWORD = "prod-master-2024!"
def connect():
    import psycopg2
    return psycopg2.connect(host="db", user="admin", password=DB_PASSWORD)
""",
        ("hardcoded_secret",),
    ),
    Fixture(
        "buggy/hardcoded_secret.js",
        "javascript",
        """\
const AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY";
export function sign(req) { return hmac(req, AWS_SECRET_ACCESS_KEY); }
""",
        ("hardcoded_secret",),
    ),
    Fixture(
        "buggy/shell_true_user.py",
        "python",
        """\
import subprocess
def ping(host):
    subprocess.run(f"ping -c 1 {host}", shell=True)
""",
        ("shell_injection",),
    ),
    Fixture(
        "buggy/os_system_user.py",
        "python",
        """\
import os
def archive(name):
    os.system("tar czf /tmp/out.tgz " + name)
""",
        ("shell_injection",),
    ),
    Fixture(
        "buggy/pickle_loads_network.py",
        "python",
        """\
import pickle, socket
def handle(sock: socket.socket):
    data = sock.recv(4096)
    obj = pickle.loads(data)
    return obj
""",
        ("unsafe_deserialization",),
    ),
    Fixture(
        "buggy/yaml_load_unsafe.py",
        "python",
        """\
import yaml
def load_config(path):
    with open(path) as f:
        return yaml.load(f)  # unsafe Loader
""",
        ("unsafe_deserialization",),
    ),
    Fixture(
        "buggy/md5_password.py",
        "python",
        """\
import hashlib
def hash_password(pw: str) -> str:
    return hashlib.md5(pw.encode()).hexdigest()
""",
        ("weak_crypto",),
    ),
    Fixture(
        "buggy/sha1_password.py",
        "python",
        """\
import hashlib
def check(pw: str, expected: str) -> bool:
    return hashlib.sha1(pw.encode()).hexdigest() == expected
""",
        ("weak_crypto",),
    ),
    Fixture(
        "buggy/eval_user_input.py",
        "python",
        """\
def calculator(expr: str):
    return eval(expr)
""",
        ("code_injection",),
    ),
    Fixture(
        "buggy/exec_user_input.py",
        "python",
        """\
def run(code: str):
    exec(code)
""",
        ("code_injection",),
    ),
    Fixture(
        "buggy/path_traversal.py",
        "python",
        """\
from flask import Flask, request
app = Flask(__name__)
@app.route("/read")
def read():
    name = request.args["f"]
    with open("/var/data/" + name) as fh:
        return fh.read()
""",
        ("path_traversal",),
    ),
    Fixture(
        "buggy/ssrf_requests.py",
        "python",
        """\
import requests
def fetch(url):
    return requests.get(url).text
def handler(req):
    return fetch(req.params["u"])
""",
        ("ssrf",),
    ),
    Fixture(
        "buggy/xss_flask.py",
        "python",
        """\
from flask import Flask, request
from markupsafe import Markup
app = Flask(__name__)
@app.route("/hi")
def hi():
    return Markup("<h1>Hello " + request.args.get("name", "") + "</h1>")
""",
        ("xss",),
    ),
    Fixture(
        "buggy/weak_random_token.py",
        "python",
        """\
import random, string
def new_token():
    return "".join(random.choice(string.ascii_letters) for _ in range(32))
""",
        ("weak_crypto",),
    ),
    Fixture(
        "buggy/tls_verify_disabled.py",
        "python",
        """\
import requests
def charge(card):
    return requests.post("https://pay.example.com/charge", json=card, verify=False)
""",
        ("tls_disabled",),
    ),
    Fixture(
        "buggy/xxe.py",
        "python",
        """\
import xml.etree.ElementTree as ET
def parse(xml_bytes):
    return ET.fromstring(xml_bytes)  # vulnerable to XXE with external entities
""",
        ("xxe",),
    ),
    Fixture(
        "buggy/command_injection_node.js",
        "javascript",
        """\
const { exec } = require("child_process");
module.exports = function lookup(domain, cb) {
  exec("whois " + domain, cb);
};
""",
        ("shell_injection",),
    ),
    Fixture(
        "buggy/prototype_pollution.js",
        "javascript",
        """\
function merge(target, src) {
  for (const k in src) {
    if (typeof src[k] === "object") merge(target[k] = target[k] || {}, src[k]);
    else target[k] = src[k];
  }
  return target;
}
module.exports = (req, res) => res.json(merge({}, req.body));
""",
        ("prototype_pollution",),
    ),
    Fixture(
        "buggy/open_redirect.py",
        "python",
        """\
from flask import Flask, request, redirect
app = Flask(__name__)
@app.route("/go")
def go():
    return redirect(request.args["next"])
""",
        ("open_redirect",),
    ),
    Fixture(
        "buggy/insecure_cookie.py",
        "python",
        """\
from flask import Flask, make_response
app = Flask(__name__)
@app.route("/login")
def login():
    resp = make_response("ok")
    resp.set_cookie("session", "abc123")  # no secure/httponly/samesite
    return resp
""",
        ("insecure_cookie",),
    ),
    Fixture(
        "buggy/timing_attack_compare.py",
        "python",
        """\
def check_api_key(provided: str, expected: str) -> bool:
    return provided == expected  # not constant time
""",
        ("timing_attack",),
    ),
    Fixture(
        "buggy/fixed_iv_aes.py",
        "python",
        """\
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
IV = b"0000000000000000"
def encrypt(key, data):
    c = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    return c.update(data) + c.finalize()
""",
        ("weak_crypto",),
    ),
    Fixture(
        "buggy/mutable_default_arg.py",
        "python",
        """\
def append_user(user, users=[]):
    users.append(user)
    return users
""",
        ("mutable_default",),
    ),
    Fixture(
        "buggy/bare_except_swallow.py",
        "python",
        """\
def safe_int(s):
    try:
        return int(s)
    except:
        pass
""",
        ("silent_exception",),
    ),
    Fixture(
        "buggy/race_check_open.py",
        "python",
        """\
import os
def safe_write(path, data):
    if not os.path.exists(path):
        with open(path, "w") as f:  # TOCTOU race
            f.write(data)
""",
        ("race_condition",),
    ),
    Fixture(
        "buggy/marshal_loads.py",
        "python",
        """\
import marshal
def load(blob):
    return marshal.loads(blob)
""",
        ("unsafe_deserialization",),
    ),
]


# Clean fixtures: code that looks similar to the buggy ones but is safe.
# Kept short. Each file intentionally has NO critical issue at confidence >=0.5.
CLEAN: list[Fixture] = [
    Fixture(
        "clean/parametrized_sql.py",
        "python",
        """\
def find_user(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
    return cur.fetchall()
""",
        (),
    ),
    Fixture(
        "clean/env_api_key.py",
        "python",
        """\
import os, requests
def call():
    key = os.environ["API_KEY"]
    return requests.get("https://api.example.com/v1/me", headers={"Authorization": f"Bearer {key}"})
""",
        (),
    ),
    Fixture(
        "clean/subprocess_list.py",
        "python",
        """\
import subprocess
def ping(host: str):
    subprocess.run(["ping", "-c", "1", host], check=True)
""",
        (),
    ),
    Fixture(
        "clean/bcrypt_password.py",
        "python",
        """\
import bcrypt
def hash_password(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())
""",
        (),
    ),
    Fixture(
        "clean/safe_yaml.py",
        "python",
        """\
import yaml
def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)
""",
        (),
    ),
    Fixture(
        "clean/safe_pickle_local.py",
        "python",
        """\
import pickle
from pathlib import Path
LOCAL_CACHE = Path("/var/app/cache.bin")
def load_local():
    # Local, application-controlled file; not from network.
    with LOCAL_CACHE.open("rb") as f:
        return pickle.load(f)
""",
        (),
    ),
    Fixture(
        "clean/secrets_token.py",
        "python",
        """\
import secrets
def new_token():
    return secrets.token_urlsafe(32)
""",
        (),
    ),
    Fixture(
        "clean/tls_enabled.py",
        "python",
        """\
import requests
def charge(card):
    return requests.post("https://pay.example.com/charge", json=card, timeout=10)
""",
        (),
    ),
    Fixture(
        "clean/defused_xml.py",
        "python",
        """\
from defusedxml import ElementTree as ET
def parse(xml_bytes):
    return ET.fromstring(xml_bytes)
""",
        (),
    ),
    Fixture(
        "clean/hmac_compare.py",
        "python",
        """\
import hmac
def check_api_key(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided, expected)
""",
        (),
    ),
    Fixture(
        "clean/aes_random_iv.py",
        "python",
        """\
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
def encrypt(key, data):
    iv = os.urandom(16)
    c = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return iv + c.update(data) + c.finalize()
""",
        (),
    ),
    Fixture(
        "clean/immutable_default.py",
        "python",
        """\
def append_user(user, users=None):
    users = list(users or [])
    users.append(user)
    return users
""",
        (),
    ),
    Fixture(
        "clean/narrow_except.py",
        "python",
        """\
def safe_int(s):
    try:
        return int(s)
    except ValueError:
        return None
""",
        (),
    ),
    Fixture(
        "clean/atomic_write.py",
        "python",
        """\
import os, tempfile
def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise
""",
        (),
    ),
    Fixture(
        "clean/flask_render.py",
        "python",
        """\
from flask import Flask, render_template, request
app = Flask(__name__)
@app.route("/hi")
def hi():
    return render_template("hi.html", name=request.args.get("name", ""))
""",
        (),
    ),
    Fixture(
        "clean/safe_redirect.py",
        "python",
        """\
from urllib.parse import urlparse
from flask import Flask, request, redirect, abort
app = Flask(__name__)
ALLOWED = {"example.com", "www.example.com"}
@app.route("/go")
def go():
    target = request.args["next"]
    if urlparse(target).hostname not in ALLOWED:
        abort(400)
    return redirect(target)
""",
        (),
    ),
    Fixture(
        "clean/secure_cookie.py",
        "python",
        """\
from flask import Flask, make_response
app = Flask(__name__)
@app.route("/login")
def login():
    r = make_response("ok")
    r.set_cookie("session", "abc123", secure=True, httponly=True, samesite="Lax")
    return r
""",
        (),
    ),
    Fixture(
        "clean/exec_child_process.js",
        "javascript",
        """\
const { execFile } = require("child_process");
module.exports = function lookup(domain, cb) {
  execFile("whois", [domain], cb);
};
""",
        (),
    ),
    Fixture(
        "clean/pure_utils.js",
        "javascript",
        """\
export function slugify(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
export function clamp(n, lo, hi) { return Math.min(Math.max(n, lo), hi); }
""",
        (),
    ),
    Fixture(
        "clean/math_helpers.py",
        "python",
        """\
import math
def circle_area(r: float) -> float:
    return math.pi * r * r
def manhattan(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))
""",
        (),
    ),
    Fixture(
        "clean/string_format.py",
        "python",
        """\
def format_user(user) -> str:
    return f"{user.first_name} {user.last_name} <{user.email}>"
""",
        (),
    ),
    Fixture(
        "clean/iterable_sum.py",
        "python",
        """\
from collections.abc import Iterable
def total(xs: Iterable[float]) -> float:
    return sum(xs)
""",
        (),
    ),
    Fixture(
        "clean/dataclass_only.py",
        "python",
        """\
from dataclasses import dataclass
@dataclass
class Point:
    x: float
    y: float
    def norm(self) -> float:
        return (self.x * self.x + self.y * self.y) ** 0.5
""",
        (),
    ),
    Fixture(
        "clean/enum_only.py",
        "python",
        """\
from enum import Enum
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
def is_primary(c: Color) -> bool:
    return c in {Color.RED, Color.GREEN, Color.BLUE}
""",
        (),
    ),
    Fixture(
        "clean/list_comprehension.py",
        "python",
        """\
def squares(n: int) -> list[int]:
    return [i * i for i in range(n)]
""",
        (),
    ),
    Fixture(
        "clean/json_parse.py",
        "python",
        """\
import json
from pathlib import Path
def load_cfg(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))
""",
        (),
    ),
    Fixture(
        "clean/typed_function.py",
        "python",
        """\
def greet(name: str, times: int = 1) -> list[str]:
    return [f"hello, {name}"] * times
""",
        (),
    ),
    Fixture(
        "clean/generator.py",
        "python",
        """\
def chunk(xs, n):
    buf = []
    for x in xs:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
""",
        (),
    ),
    Fixture(
        "clean/context_manager.py",
        "python",
        """\
from contextlib import contextmanager
import time
@contextmanager
def timed():
    t0 = time.monotonic()
    try:
        yield
    finally:
        print(f"took {time.monotonic() - t0:.3f}s")
""",
        (),
    ),
    Fixture(
        "clean/typing_protocol.py",
        "python",
        """\
from typing import Protocol
class Named(Protocol):
    name: str
def greet(obj: Named) -> str:
    return f"hi {obj.name}"
""",
        (),
    ),
]


ALL_FIXTURES: list[Fixture] = BUGGY + CLEAN


def ensure_fixtures() -> None:
    """Write every fixture to disk under ``tests/eval/fixtures/``."""
    for fx in ALL_FIXTURES:
        path = FIXTURES_ROOT / fx.relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fx.content, encoding="utf-8")
