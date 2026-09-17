# Tests live in a package rather than a single tests.py so that they can be targeted
# as `manage.py test apps.videomanagement.tests`. Plain discovery over the app would
# also pick up the vendored SadTalker checkout, whose test_options.py files match the
# default pattern and cannot be imported on their own.
