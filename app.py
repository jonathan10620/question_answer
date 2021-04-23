from flask import Flask, render_template, g, request, session, redirect, url_for
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)


def get_current_user():
    user_result = None
    if "user" in session:
        user = session["user"]
        db = get_db()

        user_cur = db.execute(
            "select id,name,password,expert, admin from users where name = ?",
            [
                user,
            ],
        )

        user_result = user_cur.fetchone()

    return user_result


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "sqlite_db"):
        g.sqlite_db.close()


@app.route("/")
def index():
    user = get_current_user()
    db = get_db()

    ques_curs = db.execute(
        """select questions.id as question_id, questions.question_text, askers.name as asker_name, experts.name as expert_name from questions
        join users as askers on askers.id = questions.asked_by_id 
        join users as experts on experts.id = questions.expert_id 
        where questions.answer_text not null"""
    )

    question_result = ques_curs.fetchall()

    return render_template("home.html", user=user, questions=question_result)


@app.route("/test")
def test():
    user = get_current_user()
    return render_template("test.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db()
        name = request.form["name"]
        hashed_password = generate_password_hash(
            request.form["password"], method="sha256"
        )

        db.execute(
            "insert into users (name, password, expert, admin) values (?,?,?,?)",
            [name, hashed_password, "0", "0"],
        )

        db.commit()

        session["user"] = name

        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    if request.method == "POST":

        name = request.form["name"]
        password = request.form["password"]

        user_cur = db.execute(
            "select id, name, password from users where name = ?", [name]
        )

        user_result = user_cur.fetchone()

        if check_password_hash(user_result["password"], password):
            session["user"] = user_result["name"]
            return redirect(url_for("index"))
        else:
            return "password incorrect"

    return render_template("login.html")


# TODO
@app.route("/question/<int:question_id>")
def question(question_id):
    user = get_current_user()
    db = get_db()
    question_curs = db.execute(
        """select questions.question_text, questions.answer_text, askers.name as asker_name, experts.name as expert_name from questions
        join users as askers on askers.id = questions.asked_by_id 
        join users as experts on experts.id = questions.expert_id where questions.id = ?""",
        [question_id],
    )
    question = question_curs.fetchone()

    return render_template("question.html", user=user, question=question)


@app.route("/answer/<int:question_id>", methods=["GET", "POST"])
def answer(question_id):
    user = get_current_user()
    db = get_db()
    if request.method == "POST":
        answer = request.form["answer"]

        db.execute(
            "update questions set answer_text = ? where id = ?",
            [answer, question_id],
        )
        db.commit()

        return redirect(url_for("unanswered"))

    ques_curs = db.execute(
        "select id, question_text from questions where id = ?", [question_id]
    )
    question = ques_curs.fetchone()

    user = get_current_user()
    return render_template("answer.html", user=user, question=question)


@app.route("/ask", methods=["GET", "POST"])
def ask():
    user = get_current_user()
    db = get_db()

    if request.method == "POST":
        db.execute(
            """insert into questions (question_text, asked_by_id, expert_id) values (?, ?, ?)""",
            [request.form["question"], user["id"], request.form["expert"]],
        )
        db.commit()

        return redirect(url_for("question"))

    exp_cur = db.execute("select id, name from users where expert = 1")

    experts = exp_cur.fetchall()

    return render_template("ask.html", user=user, experts=experts)


@app.route("/unanswered")
def unanswered():
    user = get_current_user()
    db = get_db()

    question_curs = db.execute(
        "select questions.id, questions.question_text, questions.asked_by_id, users.name from questions join users on users.id = questions.asked_by_id where questions.answer_text is null and questions.expert_id = ?",
        [user["id"]],
    )
    questions = question_curs.fetchall()

    return render_template("unanswered.html", user=user, questions=questions)


@app.route("/users")
def users():
    user = get_current_user()
    db = get_db()

    user_cur = db.execute("select id, name,expert, admin from users")

    users_results = user_cur.fetchall()
    return render_template("users.html", user=user, users=users_results)


@app.route("/logout")
def logout():
    session.pop("user", None)

    return redirect(url_for("index"))


@app.route("/promote/<int:user_id>")
def promote(user_id):
    db = get_db()
    exp_cur = db.execute("select expert from users where id = ?", [user_id])
    user = exp_cur.fetchone()
    if user["expert"] == 0:
        db.execute("update users set expert = '1' where id = ?", [user_id])
        db.commit()
    else:
        db.execute("update users set expert = '0' where id = ?", [user_id])
        db.commit()

    return redirect(url_for("users"))


if __name__ == "__main__":
    app.run(debug=True)