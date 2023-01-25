import enchant
import string

# create dictionary for the language
# in use(en_US here)
dict = enchant.Dict("it_IT")

# list of words
words = "A natale puoi, fare quello che non puoi fare mai! A natale vai di anale e con Claudiu si puo'! A natale vai d'anale anche con blast si puo'!".translate(str.maketrans('', '', string.punctuation)).split(" ")

# find those words that may be misspelled
misspelled =[]
for word in words:
  if dict.check(word) == False:
    misspelled.append(word)
print("The misspelled words are : " + str(misspelled))

# suggest the correct spelling of
# the misspelled words
for word in misspelled:
  print("Suggestion for " + word + " : " + str(dict.suggest(word)))