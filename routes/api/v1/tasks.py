import base64
import json
import tempfile
import os
import pickle
import numpy as np
import io

import spex_common.services.Task as TaskService
import spex_common.services.Job as JobService
import spex_common.services.Utils as Utils
from spex_common.modules.logging import get_logger
from flask_restx import Namespace, Resource
from flask import request, send_file, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import tasks, responses
import matplotlib.pyplot as plt
from enum import Enum
import seaborn as sns


class VisType(str, Enum):
    scatter = 'scatter'
    boxplot = 'boxplot'


logger = get_logger('spex.backend')

namespace = Namespace('Tasks', description='Tasks CRUD operations')

namespace.add_model(tasks.tasks_model.name, tasks.tasks_model)
namespace.add_model(tasks.task_post_model.name, tasks.task_post_model)
namespace.add_model(responses.response.name, responses.response)
namespace.add_model(tasks.a_tasks_response.name, tasks.a_tasks_response)
namespace.add_model(responses.error_response.name, responses.error_response)
namespace.add_model(tasks.list_tasks_response.name, tasks.list_tasks_response)
namespace.add_model(tasks.task_get_model.name, tasks.task_get_model)


@namespace.route('/<_id>')
@namespace.param('_id', 'task id')
class TaskGetPut(Resource):
    @namespace.doc('tasks/get_one', security='Bearer')
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @namespace.marshal_with(tasks.a_tasks_response)
    @jwt_required()
    def get(self, _id):
        _task = TaskService.select(_id)
        if _task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200

        return {'success': True, 'data': _task.to_json()}, 200

    @namespace.doc('tasks/update_one', security='Bearer')
    @namespace.marshal_with(tasks.a_tasks_response)
    @namespace.expect(tasks.tasks_model)
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required()
    def put(self, _id):
        _task = TaskService.select(_id)
        if _task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200
        body = request.json
        _task = TaskService.update(_id, data=body)

        return {'success': True, 'data': _task.to_json()}, 200

    @namespace.doc('task/delete', security='Bearer')
    @namespace.marshal_with(tasks.a_tasks_response)
    @namespace.response(404, 'task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required()
    def delete(self, _id):
        _task = TaskService.select(_id)
        if _task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200

        JobService.delete_connection(_to=_task.id)
        deleted = TaskService.delete(_task.id).to_json()
        return {'success': True, 'data': deleted}, 200


@namespace.route('/image/<_id>')
@namespace.param('_id', 'task id')
class TasksGetIm(Resource):
    @namespace.doc('tasks/getimage', security='Bearer')
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    # @namespace.marshal_with(tasks.a_tasks_response)
    @jwt_required()
    def get(self, _id):
        _task = TaskService.select(_id)
        if _task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200
        _task = _task.to_json()
        if _task.get('impath') is None:
            return {'success': False, 'message': 'image not found', 'data': {}}, 200

        path = _task.get('impath')
        path = Utils.getAbsoluteRelative(path, absolute=True)

        if not os.path.exists(path):
            return {'success': False, 'message': 'image not found', 'data': {}}, 200

        try:
            with open(path, 'rb') as image:
                encoded = base64.b64encode(image.read())

                encoded = f'data:image/png;base64,{encoded.decode("utf-8")}'

                return {'success': True, 'data': {'image': encoded}}, 200
        except Exception as error:
            print(f'Error: {error}')

        return {'success': False, 'message': 'image not found', 'data': {}}, 200


@namespace.route('/list')
class TaskListPost(Resource):
    @namespace.doc('tasks/getlist', security='Bearer')
    @namespace.expect(tasks.task_post_model)
    @namespace.marshal_with(tasks.list_tasks_response)
    @namespace.response(404, 'Tasks not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required()
    def post(self):
        body = request.json
        _tasks = TaskService.select_tasks(condition='in', _key=body['ids'])
        if _tasks is None:
            return {'success': False, 'data': []}, 200
        return {'success': True, 'data': _tasks}, 200


@namespace.route('')
class TaskPost(Resource):
    @namespace.doc('tasks/update', security='Bearer')
    @namespace.expect(tasks.task_post_model)
    @namespace.marshal_with(tasks.list_tasks_response)
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required()
    def post(self):
        body = request.json
        arr = []
        for _id in body['ids']:
            data = dict(body)
            del data['ids']
            task = TaskService.update(_id, data=data)
            if task is not None:
                arr.append(task.to_json())
        return {'success': True, 'data': arr}, 200

    @namespace.doc('task/get', security='Bearer')
    @namespace.marshal_with(tasks.list_tasks_response)
    @namespace.response(200, 'list tasks current user', tasks.list_tasks_response)
    @namespace.response(404, 'tasks not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required()
    def get(self):
        author = get_jwt_identity()
        result = TaskService.select_tasks(author=author)

        if result is None:
            return {'success': False, 'message': 'tasks not found', 'data': {}}, 200

        return {'success': True, 'data': result}, 200


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


@namespace.route('/file/<_id>')
@namespace.param('_id', 'task id')
@namespace.param('key', 'key name')
class TasksGetIm(Resource):
    @namespace.doc('tasks/get_file', security='Bearer')
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    # @namespace.marshal_with(tasks.a_tasks_response)
    @jwt_required()
    def get(self, _id):
        key: str = ''
        for arg in request.args:
            key = request.args.get(arg)

        task = TaskService.select(_id)
        if task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200
        task = task.to_json()
        if task.get('result') is None:
            return {'success': False, 'message': 'result not found', 'data': {}}, 200

        path = task.get('result')
        path = Utils.getAbsoluteRelative(path, absolute=True)

        message = 'result not found'

        if not os.path.exists(path):
            return {'success': False, 'message': message, 'data': {}}, 200

        try:
            with open(path, 'rb') as infile:
                data = pickle.load(infile)

                if not key:
                    # data = json.dumps(data, cls=NumpyEncoder)
                    return {'success': True, 'data': list(data.keys())}, 200

                data = data.get(key)

                fd, temp_file_name = tempfile.mkstemp()
                # fd.close()

                if isinstance(data, np.ndarray):
                    np.savetxt(temp_file_name, data, delimiter=',')
                else:
                    data.to_csv(temp_file_name, index=None)

                return send_file(
                    temp_file_name,
                    attachment_filename=f"{_id}_result_{key}.csv",
                )

        except AttributeError as error:
            logger.warning(error)
            data = json.dumps(data, cls=NumpyEncoder)
            return {'success': True, 'data': data}, 200

        except Exception as error:
            message = str(error)
            logger.warning(error)

        return {'success': False, 'message': message, 'data': {}}, 200


@namespace.route('/vis/<_id>')
@namespace.param('_id', 'task id')
@namespace.param('key', 'key name')
@namespace.param('vis_name', 'visualisation name')
class TasksGetIm(Resource):
    @namespace.doc('tasks/visualizer', security='Bearer')
    @namespace.response(404, 'Task not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    # @namespace.marshal_with(tasks.a_tasks_response)
    # @jwt_required()
    def get(self, _id):
        key: str = ''
        vis_name: str = ''

        for k in request.args.keys():
            if k == 'key':
                key = request.args.get(k)
            if k == 'vis_name':
                vis_name = request.args.get(k)

        task = TaskService.select(_id)
        if task is None:
            return {'success': False, 'message': 'task not found', 'data': {}}, 200
        task = task.to_json()
        if task.get('result') is None:
            return {'success': False, 'message': 'result not found', 'data': {}}, 200

        path = task.get('result')
        path = Utils.getAbsoluteRelative(path, absolute=True)

        message = 'result not found'

        if not os.path.exists(path):
            return {'success': False, 'message': message, 'data': {}}, 200

        try:
            with open(path, 'rb') as infile:
                data = pickle.load(infile)

                if not key:
                    # data = json.dumps(data, cls=NumpyEncoder)
                    return {'success': True, 'data': list(data.keys())}, 200

                data = data.get(key)

                # fd, temp_file_name = tempfile.mkstemp()
                # data = json.dumps(data, cls=NumpyEncoder)
                return {'success': True, 'data': list(data.keys())}, 200
        except Exception as error:
            message = str(error)
            logger.warning(message)
        finally:

            if vis_name == VisType.scatter:

                x, y = data['centroid-0'], data['centroid-1']
                plt.scatter(x, y)
                buf = io.BytesIO()

                plt.savefig(buf, format="png")
                buf.seek(0)
                data = buf.read()
                data = base64.b64encode(data)
                data = data.decode("utf-8")

                img = '<img src="data:image/png;base64,{}">'.format(data)
                resp = make_response(img)
                resp.headers["Content-Type"] = "text/html"

                return resp

            if vis_name == VisType.boxplot:
                sns.set_theme(style="whitegrid")
                # x, y, intense = data['centroid-0'], data['centroid-1'], data['131Xe']

                ax = sns.boxplot(x="centroid-0", y="131Xe", data=data, palette="Set3")
                fig = ax.get_figure()
                buf = io.BytesIO()
                fig.savefig(buf, format="png")
                buf.seek(0)
                data = buf.read()
                data = base64.b64encode(data)
                data = data.decode("utf-8")

                img = '<img src="data:image/png;base64,{}">'.format(data)
                resp = make_response(img)
                resp.headers["Content-Type"] = "text/html"

                return resp
