#!/usr/bin/python
#
# Copyright (C) 2009 Ando Yasushi (original by Google Inc.)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# For example:
#   from waveapi import robot
#   from waveapi import events
#   import appengine_multi_robot_runner
# 
#   class FooRobot(robot.Robot):
#     def __init__(self):
#       robot.Robot.__init__(self, 'Foo')
#       self.register_handler(events.BlipSubmitted, self.on_blip_submitted)
# 
#     def on_blip_submitted(self, event, wavelet):
#       wavelet.reply('foo')
# 
#   class BarRobot(robot.Robot):
#     def __init__(self):
#       robot.Robot.__init__(self, 'Bar')
#       self.register_handler(events.BlipSubmitted, self.on_blip_submitted)
# 
#     def on_blip_submitted(self, event, wavelet):
#       wavelet.reply('bar')
# 
#   if __name__ == '__main__':
#     appengine_multi_robot_runner.compound_and_run([
#       ('foo', FooRobot()),
#       ('bar', BarRobot())
#     ])
# 
# Or you can do:
#   from waveapi import robot
#   from waveapi import events
#   import appengine_multi_robot_runner
# 
#   def on_submitted_foo(event, wavelet):
#     wavelet.reply('foo')
# 
#   def on_submitted_bar(self, event, wavelet):
#     wavelet.reply('bar')
# 
#   if __name__ == '__main__':
#     foo_robot = robot.Robot('Foo')
#     foo_robot.register_handler(events.BlipSubmitted, on_submitted_foo)
# 
#     bar_robot = robot.Robot('Bar')
#     bar_robot.register_handler(events.BlipSubmitted, on_submitted_bar)
# 
#     appengine_multi_robot_runner.compound_and_run([
#       ('foo', foo_robot),
#       ('bar', bar_robot)
#     ])

import logging
import sys

from waveapi import events
from waveapi import appengine_robot_runner

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


class CompoundRobot(object):
  def __init__(self, subdomain_dict):
    self._subdomain_dict = subdomain_dict
    self._default_robot = self._subdomain_dict[-1][1]
    for (subdomain, robot) in self._subdomain_dict:
      robot.http_post = appengine_robot_runner.appengine_post

  def associated_robot(self, host):
    for (subdomain, robot) in self._subdomain_dict:
      if host.startswith(subdomain + '.'):
        return robot
    return self._default_robot

  def register_handler(self, event_class, handler, context=None, filter=None):
    for (subdomain, robot) in self._subdomain_dict:
      robot.register_handler(event_class, handler, context, filter)

  def capabilities_xml(self, host=None):
    return self.associated_robot(host).capabilities_xml()

  def profile_json(self, name=None, host=None):
    return self.associated_robot(host).profile_json(name)

  def process_events(self, json, host=None):
    return self.associated_robot(host).process_events(json)

  def get_verification_token_info(self, host=None):
    return self.associated_robot(host).get_verification_token_info()


class CapabilitiesHandler(appengine_robot_runner.CapabilitiesHandler):
  def __init__(self, method, contenttype):
    appengine_robot_runner.CapabilitiesHandler.__init__(self, method, contenttype)

  def get(self):
    self.response.headers['Content-Type'] = self._contenttype
    self.response.out.write(self._method(host=self.request.host))


class ProfileHandler(appengine_robot_runner.ProfileHandler):
  def __init__(self, method, contenttype):
    appengine_robot_runner.ProfileHandler.__init__(self, method, contenttype)

  def get(self):
    self.response.headers['Content-Type'] = self._contenttype
    self.response.out.write(self._method(host=self.request.host))


class RobotEventHandler(appengine_robot_runner.RobotEventHandler):
  def __init__(self, robot):
    appengine_robot_runner.RobotEventHandler.__init__(self, robot)

  def post(self):
    json_body = self.request.body
    if not json_body:
      # TODO(davidbyttow): Log error?
      return

    # Redirect stdout to stderr while executing handlers. This way, any stray
    # "print" statements in bot code go to the error logs instead of breaking
    # the JSON response sent to the HTTP channel.
    saved_stdout, sys.stdout = sys.stdout, sys.stderr

    json_body = unicode(json_body, 'utf8')
    logging.info('Incoming: %s', json_body)
    json_response = self._robot.process_events(json_body, host=self.request.host)
    logging.info('Outgoing: %s', json_response)
    
    sys.stdout = saved_stdout

    # Build the response.
    self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
    self.response.out.write(json_response.encode('utf-8'))


class RobotVerifyTokenHandler(appengine_robot_runner.RobotVerifyTokenHandler):
  def __init__(self, robot):
    appengine_robot_runner.RobotVerifyTokenHandler.__init__(self, robot)

  def get(self):
    token, st = self._robot.get_verification_token_info(host=self.request.host)
    logging.info('token=' + token)
    if token is None:
      self.error(404)
      self.response.out.write('No token set')
      return
    if not st is None:
      if self.request.get('st') != st:
        self.response.out.write('Invalid st value passed')
        return
    self.response.out.write(token)


def create_robot_webapp(robot, debug=False, extra_handlers=None):
  if not extra_handlers:
    extra_handlers = []
  return webapp.WSGIApplication([('/_wave/capabilities.xml',
                                  lambda: CapabilitiesHandler(robot.capabilities_xml,
                                                     'application/xml')),
                                 ('/_wave/robot/profile',
                                  lambda: ProfileHandler(robot.profile_json,
                                                     'application/json')),
                                 ('/_wave/robot/jsonrpc',
                                  lambda: RobotEventHandler(robot)),
                                 ('/_wave/verify_token',
                                  lambda: RobotVerifyTokenHandler(robot)),
                                ] + extra_handlers,
                                debug=debug)


def compound_and_run(subdomain_dict, debug=False, log_errors=True, extra_handlers=None):
  run(CompoundRobot(subdomain_dict), debug, log_errors, extra_handlers)


def run(robot, debug=False, log_errors=True, extra_handlers=None):
  # App Engine expects to construct a class with no arguments, so we
  # pass a lambda that constructs the appropriate handler with
  # arguments from the enclosing scope.
  if log_errors:
    robot.register_handler(events.OperationError, appengine_robot_runner.operation_error_handler)
  app = create_robot_webapp(robot, debug, extra_handlers)
  run_wsgi_app(app)
