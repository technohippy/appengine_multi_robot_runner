appengine_multi_robot_runner
============================

This library allows you to run multiple robots on one GAE slot.

How to use
----------

### Recommended way

If defining a class for a robot, you can store them in separate files.

    from waveapi import robot
    from waveapi import events
    import appengine_multi_robot_runner
  
    class FooRobot(robot.Robot):
      def __init__(self):
        robot.Robot.__init__(self, 'Foo')
        self.register_handler(events.BlipSubmitted, self.on_blip_submitted)
  
      def on_blip_submitted(self, event, wavelet):
        wavelet.reply('foo')
  
    class BarRobot(robot.Robot):
      def __init__(self):
        robot.Robot.__init__(self, 'Bar')
        self.register_handler(events.BlipSubmitted, self.on_blip_submitted)
  
      def on_blip_submitted(self, event, wavelet):
        wavelet.reply('bar')
  
    if __name__ == '__main__':
      appengine_multi_robot_runner.compound_and_run([
        ('foo', FooRobot()),
        ('bar', BarRobot())
      ])

### Or, you can do

    from waveapi import robot
    from waveapi import events
    import appengine_multi_robot_runner
  
    def on_submitted_foo(event, wavelet):
      wavelet.reply('foo')
  
    def on_submitted_bar(self, event, wavelet):
      wavelet.reply('bar')
  
    if __name__ == '__main__':
      foo_robot = robot.Robot('Foo')
      foo_robot.register_handler(events.BlipSubmitted, on_submitted_foo)
  
      bar_robot = robot.Robot('Bar')
      bar_robot.register_handler(events.BlipSubmitted, on_submitted_bar)
  
      appengine_multi_robot_runner.compound_and_run([
        ('foo', foo_robot),
        ('bar', bar_robot)
      ])
