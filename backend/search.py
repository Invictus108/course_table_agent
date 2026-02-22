from embedding_search import embed_text

print(embed_text("hello world"))

# TODO: get data from form
#   - types (STEM/humanities)
#   - # of classes
#   - what is wanted for semester
#   - major

# TODO: embed classes into embeddings
#   - filter out classes user has already taken
#   - filter out classes by course code (Ex: only include 2000 level classes?) (add option to form?)
#   - filter out repeats by course title (use set())
#   - weighted sum of title and description ()
#   

# TODO: create person embedding
#   - weighted sum of previous classes and description (50/50?)


# ratio of departments of classes and preserve? (EX: 20% engl, 50% cs, 30% math)
# get major requirments

# TODO: get similar embeddings (top5*k)

# IMPORTANT: we want noise so users can try different scedules
# randomly select K for them and give them to LLM along with person info for final choice
# IMPORTANT: make sure times work