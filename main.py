import json
from pathlib import Path
from typing import Optional

from deta import Deta
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status

from pyopera.combine_opera_house_with_vangelis import calculate_final_list
from pyopera.common import create_key_for_visited_performance, load_deta_project_key

# from fastapi_utils.tasks import repeat_every

# from tqdm import tqdm


deta = Deta(load_deta_project_key())

manual_db = deta.Base("manual_entries")
program_db = deta.Base("p_entries")

drive = deta.Drive("final_db")

# b = json.loads(
#     Path(
#         "/mnt/c/Users/papal/Documents/fun_stuff/pyopera/db/vangelis_excel_converted.json"
#     ).read_text()
# )["data"]


# from icecream import ic

# for i, p in tqdm(list(enumerate(b[:]))):
#     key = create_key_for_visited_performance(p)

#     db.put(p, key=key)


# ic(db.fetch().count, len(b))

# exit()
app = FastAPI()


def get_vangelid_db() -> list:
    elements = manual_db.fetch().items
    return elements


@app.get("/vangelis_db")
async def serve_vangleis_db():
    return get_vangelid_db()


@app.on_event("startup")
async def load_final_db() -> None:
    db = await calculate_final_list()
    db_str = json.dumps(db)

    drive.put("final_db.json", db_str)


@app.get("/final_db")
async def serve_final_db():
    return json.loads(drive.get("final_db.json").read())


@app.post("/add_new_performance_seen")
def add_new_performance_to_manual_db(
    request: Request, background_tasks: BackgroundTasks
):

    import asyncio as aio

    new_data = aio.run(request.json())

    key = create_key_for_visited_performance(new_data)

    existing_entry_maybe = manual_db.get(key)

    if existing_entry_maybe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted element already in DB",
        )

    background_tasks.add_task(load_final_db)
    manual_db.put(new_data, key=key)


@app.delete("/vangelis_db/{key}")
async def delete_existing_key(key: str):

    manual_db.delete(key)
