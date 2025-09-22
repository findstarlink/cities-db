import sqlite3
import os
import sys
import argparse
from tokenizers import Tokenizer, models, trainers, pre_tokenizers
import array

# Usage: python tokenize_names.py <input_db> <output_db>


def extract_names(conn):
    names = []
    # Extract city names
    for row in conn.execute("SELECT city_name FROM cities"):
        names.append(row[0])
    # Extract region names
    for row in conn.execute("SELECT region_name FROM regions"):
        names.append(row[0])
    # Extract country names
    for row in conn.execute("SELECT country_name FROM countries"):
        names.append(row[0])
    return names


def train_tokenizer(names, vocab_size):
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.BpeTrainer(special_tokens=["<unk>"], vocab_size=vocab_size)
    tokenizer.train_from_iterator(names, trainer)
    return tokenizer


def tokenize_and_write(input_db, output_db, tokenizer):
    conn_in = sqlite3.connect(input_db)
    conn_out = sqlite3.connect(output_db)
    cur_in = conn_in.cursor()
    cur_out = conn_out.cursor()

    # Copy schema except for name columns, use TEXT for *_tokens
    for table in ["cities", "regions", "countries"]:
        cur_in.execute(f"PRAGMA table_info({table})")
        columns = cur_in.fetchall()
        new_columns = []
        for col in columns:
            if col[1] in ("city_name", "region_name", "country_name"):
                new_columns.append(f"{col[1]}_tokens TEXT")
            else:
                new_columns.append(f"{col[1]} {col[2]}")
        cur_out.execute(f"CREATE TABLE {table} ({', '.join(new_columns)})")

    # Copy and tokenize data, store tokens as comma-separated text
    for table, name_col in [("cities", "city_name"), ("regions", "region_name"), ("countries", "country_name")]:
        cur_in.execute(f"SELECT * FROM {table}")
        rows = cur_in.fetchall()
        col_names = [desc[0] for desc in cur_in.description]
        name_idx = col_names.index(name_col)
        for row in rows:
            row = list(row)
            tokens = tokenizer.encode(row[name_idx]).ids
            row[name_idx] = ",".join(map(str, tokens))
            cur_out.execute(f"INSERT INTO {table} VALUES ({', '.join(['?']*len(row))})", row)

    # Write vocabulary table
    cur_out.execute("CREATE TABLE vocabulary (token_id INTEGER PRIMARY KEY, token TEXT)")
    for token, id in tokenizer.get_vocab().items():
        cur_out.execute("INSERT INTO vocabulary (token_id, token) VALUES (?, ?)", (id, token))

    conn_out.commit()
    conn_in.close()
    conn_out.close()


def main():
    parser = argparse.ArgumentParser(
        description="Tokenize names in a SQLite DB and store tokens as space-separated text."
    )
    parser.add_argument("input_db", help="Input SQLite database file")
    parser.add_argument("output_db", help="Output SQLite database file")
    parser.add_argument("--vocab-size", type=int, default=1000, help="Vocabulary size for tokenizer (default: 5000)")
    args = parser.parse_args()

    if not os.path.exists(args.input_db):
        print(f"Input DB {args.input_db} does not exist.")
        sys.exit(1)
    conn = sqlite3.connect(args.input_db)
    names = extract_names(conn)
    tokenizer = train_tokenizer(names, args.vocab_size)
    conn.close()
    tokenize_and_write(args.input_db, args.output_db, tokenizer)
    print(f"Tokenized DB written to {args.output_db}")


if __name__ == "__main__":
    main()
