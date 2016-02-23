from flask import Blueprint, render_template, abort, g, session, redirect, jsonify
from jinja2 import TemplateNotFound
from asmlearner.middleware import *
from hashlib import sha1
from asmlearner.library.pagination import Pagination
from asmlearner.library.compiler.asm import compileProblem
from redis import Redis
from rq import Queue

q = Queue(connection=Redis())
problem = Blueprint('prob', __name__)

@problem.route('/problems')
@login_required
def problem_list():
    page = int(request.args.get('p')) if 'p' in request.args else 1
    div = 20

    problem_count = g.db.query('SELECT count(*) as count FROM problem', isSingle=True)['count']
    problems = g.db.query('SELECT p.id,p.name,p.category FROM problem as p limit ?,?', ((page-1)*div, div))

    pagination = Pagination(page, div, problem_count)
    return render_template('problems.html', title='Problems', pagination=pagination, problems=problems)

@problem.route('/problem/<int:prob_id>')
@login_required
def problem_(prob_id):
    problem = g.db.query('SELECT p.id,p.name,p.category,p.answer_regex,p.instruction,p.suffix,p.example,p.category,p.status FROM problem AS p WHERE id=?', (prob_id,), True)

    return render_template('problem.html', problem=problem)

@problem.route('/problem/<int:prob_id>/submit', methods=['POST'])
@login_required
def problem_run(prob_id):
    code = request.form['code']

    try:
        prob = g.db.query('SELECT * FROM problem where id = ?', (prob_id,), isSingle=True)
        solved_id = g.db.execute('INSERT INTO solved ( ' \
                    'problem, status, answer, errmsg) VALUES ' \
                    '(?, ?, ?, ?)', (prob_id, 'COMPILE', code, ''))
        g.db.commit()

        solved = g.db.query('SELECT * FROM solved where id = ?', (solved_id,), isSingle=True)
        q.enqueue(compileProblem, prob, solved)
        return jsonify(status='success')
    except Exception as e:
        print(e)
        g.db.rollback()
        return jsonify(status='fail')
