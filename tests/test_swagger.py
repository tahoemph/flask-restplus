# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from textwrap import dedent

from flask import url_for, Blueprint
from flask.ext import restplus
from werkzeug.datastructures import FileStorage

from . import TestCase


class SwaggerTestCase(TestCase):
    def build_api(self, **kwargs):
        if 'prefix' in kwargs:
            blueprint = Blueprint('api', __name__, url_prefix=kwargs.pop('prefix'))
        else:
            blueprint = Blueprint('api', __name__)
        api = restplus.Api(blueprint, **kwargs)
        self.app.register_blueprint(blueprint)
        return api

    def get_specs(self, prefix='', app=None, status=200):
        '''Get a Swagger specification for a RestPlus API'''
        with self.app.test_client() as client:
            response = client.get('{0}/swagger.json'.format(prefix))
            self.assertEquals(response.status_code, status)
            self.assertEquals(response.content_type, 'application/json')
            return json.loads(response.data.decode('utf8'))

    def test_specs_endpoint(self):
        api = restplus.Api()
        api.init_app(self.app)

        data = self.get_specs('')
        self.assertEqual(data['swagger'], '2.0')
        self.assertEqual(data['basePath'], '/')
        self.assertEqual(data['produces'], ['application/json'])
        self.assertEqual(data['consumes'], ['application/json'])
        self.assertEqual(data['paths'], {})
        self.assertIn('info', data)

    def test_specs_endpoint_with_prefix(self):
        api = self.build_api(prefix='/api')
        # api = restplus.Api(self.app, prefix='/api')

        data = self.get_specs('/api')
        self.assertEqual(data['swagger'], '2.0')
        self.assertEqual(data['basePath'], '/api')
        self.assertEqual(data['produces'], ['application/json'])
        self.assertEqual(data['consumes'], ['application/json'])
        self.assertEqual(data['paths'], {})
        self.assertIn('info', data)

    def test_specs_endpoint_produces(self):
        api = self.build_api()

        def output_xml(data, code, headers=None):
            pass

        api.representations['application/xml'] = output_xml

        data = self.get_specs()
        self.assertEqual(len(data['produces']), 2)
        self.assertIn('application/json', data['produces'])
        self.assertIn('application/xml', data['produces'])

    def test_specs_endpoint_info(self):
        api = restplus.Api(version='1.0',
            title='My API',
            description='This is a testing API',
            terms_url='http://somewhere.com/terms/',
            contact='Support',
            contact_url='http://support.somewhere.com',
            contact_email='contact@somewhere.com',
            license='Apache 2.0',
            license_url='http://www.apache.org/licenses/LICENSE-2.0.html'
        )
        api.init_app(self.app)

        data = self.get_specs()
        self.assertEqual(data['swagger'], '2.0')
        self.assertEqual(data['basePath'], '/')
        self.assertEqual(data['produces'], ['application/json'])
        self.assertEqual(data['paths'], {})

        self.assertIn('info', data)
        self.assertEqual(data['info']['title'], 'My API')
        self.assertEqual(data['info']['version'], '1.0')
        self.assertEqual(data['info']['description'], 'This is a testing API')
        self.assertEqual(data['info']['termsOfService'], 'http://somewhere.com/terms/')
        self.assertEqual(data['info']['contact'], {
            'name': 'Support',
            'url': 'http://support.somewhere.com',
            'email': 'contact@somewhere.com',
        })
        self.assertEqual(data['info']['license'], {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html',
        })

    def test_specs_endpoint_info_delayed(self):
        api = restplus.Api(version='1.0')
        api.init_app(self.app,
            title='My API',
            description='This is a testing API',
            terms_url='http://somewhere.com/terms/',
            contact='Support',
            contact_url='http://support.somewhere.com',
            contact_email='contact@somewhere.com',
            license='Apache 2.0',
            license_url='http://www.apache.org/licenses/LICENSE-2.0.html'
        )

        data = self.get_specs()

        self.assertEqual(data['swagger'], '2.0')
        self.assertEqual(data['basePath'], '/')
        self.assertEqual(data['produces'], ['application/json'])
        self.assertEqual(data['paths'], {})

        self.assertIn('info', data)
        self.assertEqual(data['info']['title'], 'My API')
        self.assertEqual(data['info']['version'], '1.0')
        self.assertEqual(data['info']['description'], 'This is a testing API')
        self.assertEqual(data['info']['termsOfService'], 'http://somewhere.com/terms/')
        self.assertEqual(data['info']['contact'], {
            'name': 'Support',
            'url': 'http://support.somewhere.com',
            'email': 'contact@somewhere.com',
        })
        self.assertEqual(data['info']['license'], {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html',
        })

    def test_specs_authorizations(self):
        authorizations = {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        }
        restplus.Api(self.app, authorizations=authorizations)

        data = self.get_specs()

        self.assertIn('securityDefinitions', data)
        self.assertEqual(data['securityDefinitions'], authorizations)

    def test_minimal_documentation(self):
        api = self.build_api(prefix='/api')
        ns = api.namespace('ns', 'Test namespace')

        @ns.route('/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                return {}

        data = self.get_specs('/api')
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        self.assertIn('/ns/', paths)
        self.assertIn('get', paths['/ns/'])
        op = paths['/ns/']['get']
        self.assertEqual(op['tags'], ['ns'])
        self.assertEqual(op['operationId'], 'get_test_resource')
        self.assertNotIn('parameters', op)
        self.assertNotIn('summary', op)
        self.assertNotIn('description', op)
        self.assertEqual(op['responses'], {
            '200': {
                'description': 'Success',
            }
        })

        with self.context():
            self.assertEqual(url_for('api.test'), '/api/ns/')

    def test_default_ns_resource_documentation(self):
        api = self.build_api(prefix='/api', version='1.0')

        @api.route('/test/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                return {}

        data = self.get_specs('/api')
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        self.assertIn('/test/', paths)
        self.assertIn('get', paths['/test/'])
        op = paths['/test/']['get']
        self.assertEqual(op['tags'], ['default'])
        self.assertEqual(op['responses'], {
            '200': {
                'description': 'Success',
            }
        })

        self.assertEqual(len(data['tags']), 1)
        tag = data['tags'][0]
        self.assertEqual(tag['name'], 'default')
        self.assertEqual(tag['description'], 'Default namespace')

        with self.context():
            self.assertEqual(url_for('api.test'), '/api/test/')

    def test_default_ns_resource_documentation_with_override(self):
        api = self.build_api(default='site', default_label='Site namespace')

        @api.route('/test/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                return {}

        data = self.get_specs()
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        self.assertIn('/test/', paths)
        self.assertIn('get', paths['/test/'])
        op = paths['/test/']['get']
        self.assertEqual(op['tags'], ['site'])
        self.assertEqual(op['responses'], {
            '200': {
                'description': 'Success',
            }
        })

        self.assertEqual(len(data['tags']), 1)
        tag = data['tags'][0]
        self.assertEqual(tag['name'], 'site')
        self.assertEqual(tag['description'], 'Site namespace')

        with self.context():
            self.assertEqual(url_for('api.test'), '/test/')

    def test_ns_resource_documentation(self):
        api = self.build_api(prefix='/api')
        ns = api.namespace('ns', 'Test namespace')

        @ns.route('/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                return {}

        data = self.get_specs('/api')
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        self.assertIn('/ns/', paths)
        self.assertIn('get', paths['/ns/'])
        op = paths['/ns/']['get']
        self.assertEqual(op['tags'], ['ns'])
        self.assertEqual(op['responses'], {
            '200': {
                'description': 'Success',
            }
        })
        self.assertNotIn('parameters', op)

        self.assertEqual(len(data['tags']), 2)
        tag = data['tags'][-1]
        self.assertEqual(tag['name'], 'ns')
        self.assertEqual(tag['description'], 'Test namespace')

        with self.context():
            self.assertEqual(url_for('api.test'), '/api/ns/')

    def test_ns_resource_documentation_lazy(self):
        api = restplus.Api()
        ns = api.namespace('ns', 'Test namespace')

        @ns.route('/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                return {}

        api.init_app(self.app)

        data = self.get_specs()
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        self.assertIn('/ns/', paths)
        self.assertIn('get', paths['/ns/'])
        op = paths['/ns/']['get']
        self.assertEqual(op['tags'], ['ns'])
        self.assertEqual(op['responses'], {
            '200': {
                'description': 'Success',
            }
        })

        self.assertEqual(len(data['tags']), 2)
        tag = data['tags'][-1]
        self.assertEqual(tag['name'], 'ns')
        self.assertEqual(tag['description'], 'Test namespace')

        with self.context():
            self.assertEqual(url_for('test'), '/ns/')

    def test_methods_docstring_to_summary(self):
        api = self.build_api()

        @api.route('/test/', endpoint='test')
        class TestResource(restplus.Resource):
            def get(self):
                '''
                GET operation
                '''
                return {}

            def post(self):
                '''POST operation.

                Should be ignored
                '''
                return {}

            def put(self):
                '''PUT operation. Should be ignored'''
                return {}

            def delete(self):
                '''
                DELETE operation.
                Should be ignored.
                '''
                return {}

        data = self.get_specs()
        path = data['paths']['/test/']

        self.assertEqual(len(path.keys()), 4)

        for method in path.keys():
            operation = path[method]
            self.assertIn(method, ('get', 'post', 'put', 'delete'))
            self.assertEqual(operation['summary'], '{0} operation'.format(method.upper()))
            self.assertEqual(operation['operationId'], '{0}_test_resource'.format(method.lower()))
            # self.assertEqual(operation['parameters'], [])

    def test_path_parameter_no_type(self):
        api = self.build_api()

        @api.route('/id/<id>/', endpoint='by-id')
        class ByIdResource(restplus.Resource):
            def get(self, id):
                return {}

        data = self.get_specs()
        self.assertIn('/id/{id}/', data['paths'])

        op = data['paths']['/id/{id}/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'id')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)

    def test_path_parameter_with_type(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name')
        class ByNameResource(restplus.Resource):
            def get(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)

    def test_path_parameter_with_explicit_details(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name')
        class ByNameResource(restplus.Resource):
            @api.doc(params={
                'age': {'description': 'An age'}
            })
            def get(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'An age')

    def test_parser_parameters(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('param', type=int, help='Some param')

        @api.route('/with-parser/', endpoint='with-parser')
        class WithParserResource(restplus.Resource):
            @api.doc(parser=parser)
            def get(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'param')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'Some param')

    def test_parser_parameters_on_class(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('param', type=int, help='Some param')

        @api.route('/with-parser/', endpoint='with-parser')
        @api.doc(parser=parser)
        class WithParserResource(restplus.Resource):
            def get(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'param')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'Some param')

    def test_method_parser_on_class(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('param', type=int, help='Some param')

        @api.route('/with-parser/', endpoint='with-parser')
        @api.doc(get={'parser': parser})
        class WithParserResource(restplus.Resource):
            def get(self):
                return {}

            def post(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'param')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'Some param')

        op = data['paths']['/with-parser/']['post']
        self.assertNotIn('parameters', op)

    def test_parser_parameters_override(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('param', type=int, help='Some param')

        @api.route('/with-parser/', endpoint='with-parser')
        class WithParserResource(restplus.Resource):
            @api.doc(parser=parser, params={'param': {'description': 'New description'}})
            def get(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'param')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'New description')

    def test_parser_parameter_in_form(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('param', type=int, help='Some param', location='form')

        @api.route('/with-parser/', endpoint='with-parser')
        class WithParserResource(restplus.Resource):
            @api.doc(parser=parser)
            def get(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'param')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'formData')
        self.assertEqual(parameter['description'], 'Some param')

        self.assertEqual(op['consumes'], ['application/x-www-form-urlencoded', 'multipart/form-data'])

    def test_parser_parameter_in_files(self):
        api = self.build_api()
        parser = api.parser()
        parser.add_argument('in_files', type=FileStorage, location='files')

        @api.route('/with-parser/', endpoint='with-parser')
        class WithParserResource(restplus.Resource):
            @api.doc(parser=parser)
            def get(self):
                return {}

        data = self.get_specs()
        self.assertIn('/with-parser/', data['paths'])

        op = data['paths']['/with-parser/']['get']
        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'in_files')
        self.assertEqual(parameter['type'], 'file')
        self.assertEqual(parameter['in'], 'formData')

        self.assertEqual(op['consumes'], ['multipart/form-data'])

    def test_explicit_parameters(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name')
        class ByNameResource(restplus.Resource):
            @api.doc(params={
                'q': {
                    'type': 'string',
                    'in': 'query',
                    'description': 'A query string',
                }
            })
            def get(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 2)

        by_name = dict((p['name'], p) for p in op['parameters'])

        parameter = by_name['age']
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)

        parameter = by_name['q']
        self.assertEqual(parameter['name'], 'q')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'A query string')

    def test_class_explicit_parameters(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name', doc={
            'params': {
                'q': {
                    'type': 'string',
                    'in': 'query',
                    'description': 'A query string',
                }
            }
        })
        class ByNameResource(restplus.Resource):
            def get(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 2)

        by_name = dict((p['name'], p) for p in op['parameters'])

        parameter = by_name['age']
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)

        parameter = by_name['q']
        self.assertEqual(parameter['name'], 'q')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'A query string')

    def test_explicit_parameters_override(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name', doc={
            'params': {
                'q': {
                    'type': 'string',
                    'in': 'query',
                    'description': 'Overriden description',
                },
                'age': {
                    'description': 'An age'
                }
            }
        })
        class ByNameResource(restplus.Resource):
            @api.doc(params={'q': {'description': 'A query string'}})
            def get(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 2)

        by_name = dict((p['name'], p) for p in op['parameters'])

        parameter = by_name['age']
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'An age')

        parameter = by_name['q']
        self.assertEqual(parameter['name'], 'q')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'A query string')

    def test_explicit_parameters_override_by_method(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name', doc={
            'get': {
                'params': {
                    'q': {
                        'type': 'string',
                        'in': 'query',
                        'description': 'A query string',
                    }
                }
            },
            'params': {
                'age': {
                    'description': 'An age'
                }
            }
        })
        class ByNameResource(restplus.Resource):
            @api.doc(params={'age': {'description': 'Overriden'}})
            def get(self, age):
                return {}

            def post(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 2)

        by_name = dict((p['name'], p) for p in op['parameters'])

        parameter = by_name['age']
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'Overriden')

        parameter = by_name['q']
        self.assertEqual(parameter['name'], 'q')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'A query string')

        op_post = op = data['paths']['/name/{age}/']['post']
        self.assertEqual(len(op_post['parameters']), 1)

        parameter = op_post['parameters'][0]
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'An age')

    def test_explicit_parameters_desription_shortcut(self):
        api = self.build_api()

        @api.route('/name/<int:age>/', endpoint='by-name', doc={
            'get': {
                'params': {
                    'q': 'A query string',
                }
            },
            'params': {
                'age': 'An age'
            }
        })
        class ByNameResource(restplus.Resource):
            @api.doc(params={'age': 'Overriden'})
            def get(self, age):
                return {}

            def post(self, age):
                return {}

        data = self.get_specs()
        self.assertIn('/name/{age}/', data['paths'])

        op = data['paths']['/name/{age}/']['get']
        self.assertEqual(len(op['parameters']), 2)

        by_name = dict((p['name'], p) for p in op['parameters'])

        parameter = by_name['age']
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'Overriden')

        parameter = by_name['q']
        self.assertEqual(parameter['name'], 'q')
        self.assertEqual(parameter['type'], 'string')
        self.assertEqual(parameter['in'], 'query')
        self.assertEqual(parameter['description'], 'A query string')

        op_post = op = data['paths']['/name/{age}/']['post']
        self.assertEqual(len(op_post['parameters']), 1)

        parameter = op_post['parameters'][0]
        self.assertEqual(parameter['name'], 'age')
        self.assertEqual(parameter['type'], 'integer')
        self.assertEqual(parameter['in'], 'path')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'An age')

    def test_response_on_method(self):
        api = self.build_api()

        api.model('ErrorModel', {
            'message': restplus.fields.String,
        })

        @api.route('/test/')
        class ByNameResource(restplus.Resource):
            @api.doc(responses={
                404: 'Not found',
                405: ('Some message', 'ErrorModel'),
            })
            def get(self):
                return {}

        data = self.get_specs('')
        paths = data['paths']
        self.assertEqual(len(paths.keys()), 1)

        op = paths['/test/']['get']
        self.assertEqual(op['tags'], ['default'])
        self.assertEqual(op['responses'], {
            # '200': {
            #     'description': 'Success',
            # },
            '404': {
                'description': 'Not found',
            },
            '405': {
                'description': 'Some message',
                'schema': {
                    '$ref': '#/definitions/ErrorModel',
                }
            }
        })

        self.assertIn('definitions', data)
        self.assertIn('ErrorModel', data['definitions'])

    def test_description(self):
        api = self.build_api()

        @api.route('/description/', endpoint='description', doc={
            'description': 'Parent description.',
            'delete': {'description': 'A delete operation'},
        })
        class ResourceWithDescription(restplus.Resource):
            @api.doc(description='Some details')
            def get(self):
                return {}

            def post(self):
                '''
                Do something.

                Extra description
                '''
                return {}

            def put(self):
                '''No description (only summary)'''

            def delete(self):
                '''No description (only summary)'''

        @api.route('/descriptionless/', endpoint='descriptionless')
        class ResourceWithoutDescription(restplus.Resource):
            def get(self):
                '''No description (only summary)'''
                return {}

        data = self.get_specs()

        description = lambda m: data['paths']['/description/'][m]['description']

        self.assertEqual(description('get'), dedent('''\
            Parent description.
            Some details'''
        ))

        self.assertEqual(description('post'), dedent('''\
            Parent description.
            Extra description'''
        ))

        self.assertEqual(description('delete'), dedent('''\
            Parent description.
            A delete operation'''
        ))

        self.assertEqual(description('put'), 'Parent description.')
        self.assertNotIn('description', data['paths']['/descriptionless/']['get'])

    def test_operation_id(self):
        api = self.build_api()

        @api.route('/test/', endpoint='test')
        class TestResource(restplus.Resource):
            @api.doc(id='get_objects')
            def get(self):
                return {}

            def post(self):
                return {}

        data = self.get_specs()
        path = data['paths']['/test/']

        self.assertEqual(path['get']['operationId'], 'get_objects')
        self.assertEqual(path['post']['operationId'], 'post_test_resource')

    def test_custom_default_operation_id(self):
        def default_id(resource, method):
            return '{0}{1}'.format(method, resource)

        api = self.build_api(default_id=default_id)

        @api.route('/test/', endpoint='test')
        class TestResource(restplus.Resource):
            @api.doc(id='get_objects')
            def get(self):
                return {}

            def post(self):
                return {}

        data = self.get_specs()
        path = data['paths']['/test/']

        self.assertEqual(path['get']['operationId'], 'get_objects')
        self.assertEqual(path['post']['operationId'], 'postTestResource')

    def test_model_primitive_types(self):
        api = self.build_api()

        @api.route('/model-int/')
        class ModelInt(restplus.Resource):
            @api.doc(model=int)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertNotIn('definitions', data)
        self.assertEqual(data['paths']['/model-int/']['get']['responses'], {
            '200': {
                'description': 'Success',
                'schema': {
                    'type': 'integer'
                }
            }
        })

    def test_model_as_flat_dict(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

            @api.doc(model='Person')
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            # 'id': 'Person',
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema']['$ref'], '#/definitions/Person')
        self.assertEqual(path['post']['responses']['200']['schema']['$ref'], '#/definitions/Person')

    def test_model_as_nested_dict(self):
        api = self.build_api()

        address_fields = api.model('Address', {
            'road': restplus.fields.String,
        })

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
            'address': restplus.fields.Nested(address_fields)
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

            @api.doc(model='Person')
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            'required': ['address'],
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                },
                'address': {
                    '$ref': '#/definitions/Address',
                }
            }
        })

        self.assertIn('Address', data['definitions'].keys())
        self.assertEqual(data['definitions']['Address'], {
            'properties': {
                'road': {
                    'type': 'string'
                },
            }
        })

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema']['$ref'], '#/definitions/Person')
        self.assertEqual(path['post']['responses']['200']['schema']['$ref'], '#/definitions/Person')

    def test_model_as_flat_dict_with_marchal_decorator(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.marshal_with(fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema']['$ref'], '#/definitions/Person')

    def test_marchal_decorator_with_code(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.marshal_with(fields, code=204)
            def delete(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])

        path = data['paths']['/model-as-dict/']
        self.assertEqual(list(path['delete']['responses'].keys()), ['204'])
        self.assertEqual(path['delete']['responses']['204']['schema']['$ref'], '#/definitions/Person')

    def test_model_as_flat_dict_with_marchal_decorator_list(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.marshal_with(fields, as_list=True)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema'], {
            'type': 'array',
            'items': {'$ref': '#/definitions/Person'},
        })

    def test_model_as_flat_dict_with_marchal_decorator_list_alt(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.marshal_list_with(fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema'], {
            'type': 'array',
            'items': {'$ref': '#/definitions/Person'},
        })

    def test_model_as_dict_with_list(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'tags': restplus.fields.List(restplus.fields.String),
        })

        @api.route('/model-with-list/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'tags': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                }
            }
        })

        path = data['paths']['/model-with-list/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Person'})

    def test_model_list_of_primitive_types(self):
        api = self.build_api()

        @api.route('/model-list/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=[int])
            def get(self):
                return {}

            @api.doc(model=[str])
            def post(self):
                return {}

        data = self.get_specs()

        self.assertNotIn('definitions', data)

        path = data['paths']['/model-list/']
        self.assertEqual(path['get']['responses']['200']['schema'], {
            'type': 'array',
            'items': {'type': 'integer'},
        })
        self.assertEqual(path['post']['responses']['200']['schema'], {
            'type': 'array',
            'items': {'type': 'string'},
        })

    def test_model_list_as_flat_dict(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=[fields])
            def get(self):
                return {}

            @api.doc(model=['Person'])
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])

        path = data['paths']['/model-as-dict/']
        for method in 'get', 'post':
            self.assertEqual(path[method]['responses']['200']['schema'], {
                'type': 'array',
                'items': {'$ref': '#/definitions/Person'},
            })

    def test_model_doc_on_class(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        @api.doc(model=fields)
        class ModelAsDict(restplus.Resource):
            def get(self):
                return {}

            def post(self):
                return {}

        data = self.get_specs()
        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])

        path = data['paths']['/model-as-dict/']
        for method in 'get', 'post':
            self.assertEqual(path[method]['responses']['200']['schema'], {'$ref': '#/definitions/Person'})

    def test_model_doc_for_method_on_class(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        @api.doc(get={'model': fields})
        class ModelAsDict(restplus.Resource):
            def get(self):
                return {}

            def post(self):
                return {}

        data = self.get_specs()
        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])

        path = data['paths']['/model-as-dict/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Person'})
        self.assertNotIn('schema', path['post']['responses']['200'])

    def test_model_not_found(self):
        api = self.build_api()

        @api.route('/model-not-found/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model='NotFound')
            def get(self):
                return {}

        data = self.get_specs(status=500)

        self.assertEqual(data['status'], 500)

    def test_model_as_class(self):
        api = self.build_api()

        @api.model(fields={'name': restplus.fields.String})
        class MyModel(restplus.fields.Raw):
            pass

        fields = api.model('Fake', {
            'name': restplus.fields.String,
            'model': MyModel,
        })

        @api.route('/model-as-class/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Fake', data['definitions'])
        self.assertIn('MyModel', data['definitions'])
        self.assertEqual(data['definitions']['Fake'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'model': {
                    '$ref': '#/definitions/MyModel',
                }
            }
        })
        self.assertEqual(data['definitions']['MyModel'], {
            'properties': {
                'name': {
                    'type': 'string'
                }
            }
        })

        path = data['paths']['/model-as-class/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Fake'})

    def test_nested_model_as_class(self):
        api = self.build_api()

        @api.model(fields={'name': restplus.fields.String})
        class MyModel(restplus.fields.Raw):
            pass

        fields = api.model('Fake', {
            'name': restplus.fields.String,
            'nested': restplus.fields.Nested(MyModel),
        })

        @api.route('/model-as-class/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

            @api.doc(model='Fake')
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Fake', data['definitions'])
        self.assertIn('MyModel', data['definitions'])
        self.assertEqual(data['definitions']['Fake'], {
            'required': ['nested'],
            'properties': {
                'name': {
                    'type': 'string'
                },
                'nested': {
                    '$ref': '#/definitions/MyModel',
                }
            }
        })
        self.assertEqual(data['definitions']['MyModel'], {
            'properties': {
                'name': {
                    'type': 'string'
                }
            }
        })

        path = data['paths']['/model-as-class/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Fake'})
        self.assertEqual(path['post']['responses']['200']['schema'], {'$ref': '#/definitions/Fake'})

    def test_model_list_as_class(self):
        api = self.build_api()

        @api.model(fields={'name': restplus.fields.String})
        class MyModel(restplus.fields.Raw):
            pass

        fields = api.model('Fake', {
            'name': restplus.fields.String,
            'list': restplus.fields.List(MyModel),
        })

        @api.route('/model-list-as-class/')
        class ModelListAsClass(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Fake', data['definitions'])
        self.assertIn('MyModel', data['definitions'])
        self.assertEqual(data['definitions']['Fake'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'list': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/definitions/MyModel',
                    }
                }
            }
        })
        self.assertEqual(data['definitions']['MyModel'], {
            'properties': {
                'name': {
                    'type': 'string'
                }
            }
        })

        path = data['paths']['/model-list-as-class/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Fake'})

    def test_custom_field(self):
        api = self.build_api()

        @api.model(type='integer', format='int64')
        class MyModel(restplus.fields.Raw):
            pass

        fields = api.model('Fake', {
            'name': restplus.fields.String,
            'model': MyModel,
        })

        @api.route('/custom-field/')
        class CustomFieldResource(restplus.Resource):
            @api.doc(model=fields)
            def get(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Fake', data['definitions'])
        self.assertNotIn('MyModel', data['definitions'])
        self.assertEqual(data['definitions']['Fake'], {
            'properties': {
                'name': {
                    'type': 'string'
                },
                'model': {
                    'type': 'integer',
                    'format': 'int64',
                }
            }
        })

        path = data['paths']['/custom-field/']
        self.assertEqual(path['get']['responses']['200']['schema'], {'$ref': '#/definitions/Fake'})

    def test_body_model(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model='Person', body=fields)
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            # 'id': 'Person',
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        op = data['paths']['/model-as-dict/']['post']
        self.assertEqual(op['responses']['200']['schema']['$ref'], '#/definitions/Person')

        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'payload')
        self.assertEqual(parameter['in'], 'body')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['schema']['$ref'], '#/definitions/Person')
        self.assertNotIn('description', parameter)

    def test_body_model_as_tuple(self):
        api = self.build_api()

        fields = api.model('Person', {
            'name': restplus.fields.String,
            'age': restplus.fields.Integer,
            'birthdate': restplus.fields.DateTime,
        })

        @api.route('/model-as-dict/')
        class ModelAsDict(restplus.Resource):
            @api.doc(model='Person', body=(fields, 'Body description'))
            def post(self):
                return {}

        data = self.get_specs()

        self.assertIn('definitions', data)
        self.assertIn('Person', data['definitions'])
        self.assertEqual(data['definitions']['Person'], {
            # 'id': 'Person',
            'properties': {
                'name': {
                    'type': 'string'
                },
                'age': {
                    'type': 'integer'
                },
                'birthdate': {
                    'type': 'string',
                    'format': 'date-time'
                }
            }
        })

        op = data['paths']['/model-as-dict/']['post']
        self.assertEqual(op['responses']['200']['schema']['$ref'], '#/definitions/Person')

        self.assertEqual(len(op['parameters']), 1)

        parameter = op['parameters'][0]
        self.assertEqual(parameter['name'], 'payload')
        self.assertEqual(parameter['in'], 'body')
        self.assertEqual(parameter['required'], True)
        self.assertEqual(parameter['description'], 'Body description')
        self.assertEqual(parameter['schema']['$ref'], '#/definitions/Person')

    def test_authorizations(self):
        api = restplus.Api(self.app, authorizations={
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        })

        # @api.route('/authorizations/')
        # class ModelAsDict(restplus.Resource):
        #     def get(self):
        #         return {}

        #     def post(self):
        #         return {}

        data = self.get_specs()
        self.assertIn('securityDefinitions', data)
        self.assertNotIn('security', data)

        # path = data['paths']['/authorizations/']
        # self.assertNotIn('security', path['get'])
        # self.assertEqual(path['post']['security'], {'apikey': []})

    def test_single_root_security_string(self):
        api = restplus.Api(self.app, security='apikey', authorizations={
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        })

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            def post(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        })
        self.assertEqual(data['security'], [{'apikey': []}])

        op = data['paths']['/authorizations/']['post']
        self.assertNotIn('security', op)

    def test_single_root_security_object(self):
        security_definitions = {
            'oauth2': {
                'type': 'oauth2',
                'flow': 'accessCode',
                'tokenUrl': 'https://somewhere.com/token',
                'scopes': {
                    'read': 'Grant read-only access',
                    'write': 'Grant read-write access',
                }
            },
            'implicit': {
                'type': 'oauth2',
                'flow': 'implicit',
                'tokenUrl': 'https://somewhere.com/token',
                'scopes': {
                    'read': 'Grant read-only access',
                    'write': 'Grant read-write access',
                }
            }
        }

        api = restplus.Api(self.app,
            security={
                'oauth2': 'read',
                'implicit': ['read', 'write']
            },
            authorizations=security_definitions
        )

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            def post(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], security_definitions)
        self.assertEqual(data['security'], [{
            'oauth2': ['read'],
            'implicit': ['read', 'write']
        }])

        op = data['paths']['/authorizations/']['post']
        self.assertNotIn('security', op)

    def test_root_security_as_list(self):
        security_definitions = {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            },
            'oauth2': {
                'type': 'oauth2',
                'flow': 'accessCode',
                'tokenUrl': 'https://somewhere.com/token',
                'scopes': {
                    'read': 'Grant read-only access',
                    'write': 'Grant read-write access',
                }
            }
        }
        api = restplus.Api(self.app, security=['apikey', {'oauth2': 'read'}], authorizations=security_definitions)

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            def post(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], security_definitions)
        self.assertEqual(data['security'], [{'apikey': []}, {'oauth2': ['read']}])

        op = data['paths']['/authorizations/']['post']
        self.assertNotIn('security', op)

    def test_method_security(self):
        api = restplus.Api(self.app, authorizations={
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        })

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            @api.doc(security=['apikey'])
            def get(self):
                return {}

            @api.doc(security='apikey')
            def post(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            }
        })
        self.assertNotIn('security', data)

        path = data['paths']['/authorizations/']
        for method in 'get', 'post':
            self.assertEqual(path[method]['security'], [{'apikey': []}])

    def test_security_override(self):
        security_definitions = {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            },
            'oauth2': {
                'type': 'oauth2',
                'flow': 'accessCode',
                'tokenUrl': 'https://somewhere.com/token',
                'scopes': {
                    'read': 'Grant read-only access',
                    'write': 'Grant read-write access',
                }
            }
        }
        api = restplus.Api(self.app, security=['apikey', {'oauth2': 'read'}], authorizations=security_definitions)

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            @api.doc(security=[{'oauth2': ['read', 'write']}])
            def get(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], security_definitions)

        op = data['paths']['/authorizations/']['get']
        self.assertEqual(op['security'], [{'oauth2': ['read', 'write']}])

    def test_security_nullify(self):
        security_definitions = {
            'apikey': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API'
            },
            'oauth2': {
                'type': 'oauth2',
                'flow': 'accessCode',
                'tokenUrl': 'https://somewhere.com/token',
                'scopes': {
                    'read': 'Grant read-only access',
                    'write': 'Grant read-write access',
                }
            }
        }
        api = restplus.Api(self.app, security=['apikey', {'oauth2': 'read'}], authorizations=security_definitions)

        @api.route('/authorizations/')
        class ModelAsDict(restplus.Resource):
            @api.doc(security=[])
            def get(self):
                return {}

            @api.doc(security=None)
            def post(self):
                return {}

        data = self.get_specs()
        self.assertEqual(data['securityDefinitions'], security_definitions)

        path = data['paths']['/authorizations/']
        for method in 'get', 'post':
            self.assertEqual(path[method]['security'], [])

    def test_hidden_resource(self):
        api = self.build_api()

        @api.route('/test/', endpoint='test', doc=False)
        class TestResource(restplus.Resource):
            def get(self):
                '''
                GET operation
                '''
                return {}

        @api.hide
        @api.route('/test2/', endpoint='test2')
        class TestResource2(restplus.Resource):
            def get(self):
                '''
                GET operation
                '''
                return {}

        @api.doc(False)
        @api.route('/test3/', endpoint='test3')
        class TestResource3(restplus.Resource):
            def get(self):
                '''
                GET operation
                '''
                return {}

        data = self.get_specs()
        for path in '/test/', '/test2/', '/test3/':
            self.assertNotIn(path, data['paths'])

    def test_hidden_methods(self):
        api = self.build_api()

        @api.route('/test/', endpoint='test')
        @api.doc(delete=False)
        class TestResource(restplus.Resource):
            def get(self):
                '''
                GET operation
                '''
                return {}

            @api.doc(False)
            def post(self):
                '''POST operation.

                Should be ignored
                '''
                return {}

            @api.hide
            def put(self):
                '''PUT operation. Should be ignored'''
                return {}

            def delete(self):
                return {}

        data = self.get_specs()
        path = data['paths']['/test/']

        self.assertIn('get', path)
        self.assertNotIn('post', path)
        self.assertNotIn('put', path)
