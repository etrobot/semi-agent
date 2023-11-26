import re

def letterNnum(input_string:str):
  pattern = r"([a-zA-Z]+)\s+(\d+)"
  matches = re.match(pattern, input_string)
  letters = matches.group(1)
  numbers = matches.group(2)
  return ''.join(letters),int(''.join(numbers))
