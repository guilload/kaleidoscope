# Compute the x'th fibonacci number.
def fibonacci(x)
  if x < 3 then
    1
  else
    fibonacci(x - 1) + fibonacci(x - 2)

# This expression will compute the 40th number.
fibonacci(40)
