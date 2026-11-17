"""Bind a recorded user confirmation to the exact reviewed book file.

This checks file consistency, not the authenticity of a user's reply. The agent
must obtain an actual confirmation before writing the approval record.
"""
import argparse
import hashlib
import json
from pathlib import Path


def load_book(book_path):
    raw = Path(book_path).read_bytes()
    book = json.loads(raw)
    if not isinstance(book, dict):
        raise ValueError("Book must be a JSON object.")
    for key in ("title", "level", "dialect"):
        if not isinstance(book.get(key), str) or not book[key].strip():
            raise ValueError(f"Book requires a nonempty {key}.")
    pages = book.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Book requires nonempty pages.")
    for number, page in enumerate(pages, 1):
        if (not isinstance(page, dict) or type(page.get("page")) is not int
                or page["page"] != number or not isinstance(page.get("text"), str)
                or not page["text"].strip()):
            raise ValueError("Pages must have consecutive numbers and nonempty text.")
    questions = book.get("questions")
    if not isinstance(questions, list):
        raise ValueError("Book requires a questions list; use [] when omitted by the user.")
    for question in questions:
        if not isinstance(question, dict) or any(not isinstance(question.get(key), str) or not question[key].strip()
               for key in ("question", "answer")):
            raise ValueError("Each question requires question and answer text.")
    return book, hashlib.sha256(raw).hexdigest()


def load_approved_book(book_path, approval_path):
    book, digest = load_book(book_path)
    if not approval_path or not Path(approval_path).is_file():
        raise ValueError("Text confirmation is missing. Obtain the user's confirmation first.")
    approval = json.loads(Path(approval_path).read_text(encoding="utf-8"))
    if not isinstance(approval, dict) or approval.get("status") != "confirmed":
        raise ValueError("Text has not been confirmed by the user.")
    confirmation = approval.get("user_confirmation")
    if not isinstance(confirmation, str) or not confirmation.strip():
        raise ValueError("Record the actual user's confirmation, not an inferred approval.")
    if approval.get("book_sha256") != digest:
        raise ValueError("Book changed after confirmation. Review and reconfirm the new version.")
    return book


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    digest = sub.add_parser("digest", help="Inspect the content digest; does not approve it.")
    digest.add_argument("book")
    check = sub.add_parser("check", help="Check the recorded confirmation before production.")
    check.add_argument("book")
    check.add_argument("approval")
    args = parser.parse_args()
    try:
        book, digest = load_book(args.book)
        if args.command == "check":
            load_approved_book(args.book, args.approval)
        print(json.dumps({"book_sha256": digest, "title": book["title"],
                          "pages": len(book["pages"]), "dialect": book["dialect"],
                          "confirmation_matches": args.command == "check"}, ensure_ascii=False))
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
