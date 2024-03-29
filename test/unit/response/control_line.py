"""
Unit tests for the stem.response.ControlLine class.
"""

import unittest

import stem.response

# response made by having 'DataDirectory /tmp/my data\"dir/' in the torrc
PROTOCOLINFO_RESPONSE = (
  'PROTOCOLINFO 1',
  'AUTH METHODS=COOKIE COOKIEFILE="/tmp/my data\\\\\\"dir//control_auth_cookie"',
  'VERSION Tor="0.2.1.30"',
  'OK',
)


class TestControlLine(unittest.TestCase):
  def test_pop_examples(self):
    """
    Checks that the pop method's pydoc examples are correct.
    """

    line = stem.response.ControlLine("\"We're all mad here.\" says the grinning cat.")
    self.assertEquals(line.pop(True), "We're all mad here.")
    self.assertEquals(line.pop(), 'says')
    self.assertEquals(line.remainder(), 'the grinning cat.')

    line = stem.response.ControlLine('"this has a \\" and \\\\ in it" foo=bar more_data')
    self.assertEquals(line.pop(True, True), 'this has a " and \\ in it')

  def test_string(self):
    """
    Basic checks that we behave as a regular immutable string.
    """

    line = stem.response.ControlLine(PROTOCOLINFO_RESPONSE[0])
    self.assertEquals(line, 'PROTOCOLINFO 1')
    self.assertTrue(line.startswith('PROTOCOLINFO '))

    # checks that popping items doesn't effect us
    line.pop()
    self.assertEquals(line, 'PROTOCOLINFO 1')
    self.assertTrue(line.startswith('PROTOCOLINFO '))

  def test_general_usage(self):
    """
    Checks a basic use case for the popping entries.
    """

    # pops a series of basic, space separated entries
    line = stem.response.ControlLine(PROTOCOLINFO_RESPONSE[0])
    self.assertEquals(line.remainder(), 'PROTOCOLINFO 1')
    self.assertFalse(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertEquals(None, line.peek_key())

    self.assertRaises(ValueError, line.pop_mapping)
    self.assertEquals(line.pop(), 'PROTOCOLINFO')
    self.assertEquals(line.remainder(), '1')
    self.assertFalse(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertEquals(None, line.peek_key())

    self.assertRaises(ValueError, line.pop_mapping)
    self.assertEquals(line.pop(), '1')
    self.assertEquals(line.remainder(), '')
    self.assertTrue(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertEquals(None, line.peek_key())

    self.assertRaises(IndexError, line.pop_mapping)
    self.assertRaises(IndexError, line.pop)
    self.assertEquals(line.remainder(), '')
    self.assertTrue(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertEquals(None, line.peek_key())

  def test_pop_mapping(self):
    """
    Checks use cases when parsing KEY=VALUE mappings.
    """

    # version entry with a space
    version_entry = 'Tor="0.2.1.30 (0a083b0188cacd2f07838ff0446113bd5211a024)"'

    line = stem.response.ControlLine(version_entry)
    self.assertEquals(line.remainder(), version_entry)
    self.assertFalse(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertTrue(line.is_next_mapping())
    self.assertTrue(line.is_next_mapping(key = 'Tor'))
    self.assertTrue(line.is_next_mapping(key = 'Tor', quoted = True))
    self.assertTrue(line.is_next_mapping(quoted = True))
    self.assertEquals('Tor', line.peek_key())

    # try popping this as a non-quoted mapping
    self.assertEquals(line.pop_mapping(), ('Tor', '"0.2.1.30'))
    self.assertEquals(line.remainder(), '(0a083b0188cacd2f07838ff0446113bd5211a024)"')
    self.assertFalse(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertRaises(ValueError, line.pop_mapping)
    self.assertEquals(None, line.peek_key())

    # try popping this as a quoted mapping
    line = stem.response.ControlLine(version_entry)
    self.assertEquals(line.pop_mapping(True), ('Tor', '0.2.1.30 (0a083b0188cacd2f07838ff0446113bd5211a024)'))
    self.assertEquals(line.remainder(), '')
    self.assertTrue(line.is_empty())
    self.assertFalse(line.is_next_quoted())
    self.assertFalse(line.is_next_mapping())
    self.assertEquals(None, line.peek_key())

  def test_escapes(self):
    """
    Checks that we can parse quoted values with escaped quotes in it. This
    explicitely comes up with the COOKIEFILE attribute of PROTOCOLINFO
    responses.
    """

    auth_line = PROTOCOLINFO_RESPONSE[1]
    line = stem.response.ControlLine(auth_line)
    self.assertEquals(line, auth_line)
    self.assertEquals(line.remainder(), auth_line)

    self.assertEquals(line.pop(), 'AUTH')
    self.assertEquals(line.pop_mapping(), ('METHODS', 'COOKIE'))

    self.assertEquals(line.remainder(), r'COOKIEFILE="/tmp/my data\\\"dir//control_auth_cookie"')
    self.assertTrue(line.is_next_mapping())
    self.assertTrue(line.is_next_mapping(key = 'COOKIEFILE'))
    self.assertTrue(line.is_next_mapping(quoted = True))
    self.assertTrue(line.is_next_mapping(quoted = True, escaped = True))
    cookie_file_entry = line.remainder()

    # try a general pop
    self.assertEquals(line.pop(), 'COOKIEFILE="/tmp/my')
    self.assertEquals(line.pop(), r'data\\\"dir//control_auth_cookie"')
    self.assertTrue(line.is_empty())

    # try a general pop with escapes
    line = stem.response.ControlLine(cookie_file_entry)
    self.assertEquals(line.pop(escaped = True), 'COOKIEFILE="/tmp/my')
    self.assertEquals(line.pop(escaped = True), r'data\"dir//control_auth_cookie"')
    self.assertTrue(line.is_empty())

    # try a mapping pop
    line = stem.response.ControlLine(cookie_file_entry)
    self.assertEquals(line.pop_mapping(), ('COOKIEFILE', '"/tmp/my'))
    self.assertEquals(line.remainder(), r'data\\\"dir//control_auth_cookie"')
    self.assertFalse(line.is_empty())

    # try a quoted mapping pop (this should trip up on the escaped quote)
    line = stem.response.ControlLine(cookie_file_entry)
    self.assertEquals(line.pop_mapping(True), ('COOKIEFILE', '/tmp/my data\\\\\\'))
    self.assertEquals(line.remainder(), 'dir//control_auth_cookie"')
    self.assertFalse(line.is_empty())

    # try an escaped quoted mapping pop
    line = stem.response.ControlLine(cookie_file_entry)
    self.assertEquals(line.pop_mapping(True, True), ('COOKIEFILE', r'/tmp/my data\"dir//control_auth_cookie'))
    self.assertTrue(line.is_empty())

    # try an escaped slash followed by a character that could be part of an
    # escape sequence

    line = stem.response.ControlLine(r'COOKIEFILE="C:\\Users\\Atagar\\AppData\\tor\\control_auth_cookie"')
    self.assertEquals(line.pop_mapping(True, True), ('COOKIEFILE', r'C:\Users\Atagar\AppData\tor\control_auth_cookie'))
    self.assertTrue(line.is_empty())
