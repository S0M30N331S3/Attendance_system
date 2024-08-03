import pickle

encodefile_path = "Encodefile.p"

with open(encodefile_path, 'wb') as file:
    pickle.dump(([], []), file)
    print(f"{encodefile_path} has been cleared and initialized with an empty list.")
