import pickle

# Load the encode file
file_path = 'Encodefile.p'

with open(file_path, 'rb') as file:
    encodeListKnownWithIds = pickle.load(file)

# Check the contents of the encode file
encodeListKnown, Ids = encodeListKnownWithIds
{
    'num_encodings': len(encodeListKnown),
    'Ids': Ids[:10]  # Display the first 10 IDs for verification
}
print(encodeListKnownWithIds)