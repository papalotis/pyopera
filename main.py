import json
from pathlib import Path

import deta
from fastapi import FastAPI, HTTPException, Request, status

app = FastAPI()

vangelis_db_path = Path("test.json")


def load_vangelis_db() -> list:
    return json.loads(vangelis_db_path.read_text())


@app.get("/vangelis_db")
def read_root():
    return load_vangelis_db()


@app.post("/add_new_performance_seen")
def read_root(request: Request):
    import asyncio as aio

    new_data = aio.run(request.json())

    db = load_vangelis_db()

    if new_data in db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted element already in DB",
        )

    db.append(new_data)
    db.sort(key=lambda el: el["date"])

    vangelis_db_path.write_text(json.dumps(db))
