import services.Job as JobService
import datetime
from flask_restx import Namespace, Resource
from flask import request, abort
from models.Job import Job
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .models import jobs, responses

namespace = Namespace('Jobs', description='Jobs CRUD operations')

namespace.add_model(jobs.jobs_model.name, jobs.jobs_model)
namespace.add_model(responses.response.name, responses.response)
namespace.add_model(jobs.a_jobs_response.name, jobs.a_jobs_response)
namespace.add_model(responses.error_response.name, responses.error_response)
namespace.add_model(jobs.list_jobs_response.name, jobs.list_jobs_response)


@namespace.route('/')
class Items(Resource):
    @namespace.doc('jobs/create')
    @namespace.expect(jobs.jobs_model)
    @namespace.marshal_with(jobs.a_jobs_response)
    @namespace.response(200, 'Created job', jobs.a_jobs_response)
    @namespace.response(400, 'Message about reason of error', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required
    def post(self):
        body = request.json

        result = JobService.insert(body)
        return {'success': True, 'data': result}, 200

    @namespace.doc('job/get')
    @namespace.marshal_with(jobs.a_jobs_response)
    @namespace.response(404, 'jobs not found', responses.error_response)
    @namespace.response(401, 'Unauthorized', responses.error_response)
    @jwt_required
    def get(self):
        if id == 'login':
            abort(404, 'User with id:{} not found'.format(id))

        jobs = JobService.select_jobs()

        if jobs is None:
            abort(404, 'jobs not found')

        return {'success': True, 'data': jobs}, 200
