from datasets import load_dataset
import json

dataset = load_dataset("Nan-Do/code-search-net-java")

dataset['train'].to_json("my_java_data.json")
