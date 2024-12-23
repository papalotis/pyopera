import random
import string
from collections import ChainMap
from datetime import date, datetime
from typing import (
    Annotated,
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Sequence,
    TypeGuard,
    TypeVar,
)

from approx_dates.models import ApproxDate
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from more_itertools import flatten
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)
from unidecode import unidecode

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
NonEmptyStrList = Annotated[List[NonEmptyStr], Field(min_items=1)]
SHA1Str = Annotated[str, StringConstraints(pattern=r"[0-9a-f]{40}")]


def key_create_creator(key_creator: Callable[[], str]) -> Callable[[str | None], str]:
    def create_key_if_needed(key: str | None) -> str:
        if key is not None:
            return key
        value = key_creator()
        return value

    return create_key_if_needed


def create_key_for_visited_performance_v3() -> str:
    available_characters = "abcdef" + string.digits
    # create a 40 character long random string (like a sha1 hash)
    return "".join(random.choices(available_characters, k=40))


def create_deta_style_key() -> str:
    available_characters = string.ascii_lowercase + string.digits
    # create a 12 character long random
    return "".join(random.choices(available_characters, k=12))


PerformanceKey = Annotated[
    SHA1Str, AfterValidator(key_create_creator(create_key_for_visited_performance_v3))
]
DetaKey = Annotated[str, AfterValidator(key_create_creator(create_deta_style_key))]


def parse_date(v: Any) -> Optional[ApproxDate]:
    # there are three possible formats:
    # full iso format: "2020-01-01T00:00:00" (handled by datetime module)
    # partial iso format: "2020-01" (January 2020) (handled by ApproxDate)
    # short iso to short iso: "2020-01-01 to 2020-01-04" (January 1st to 4th 2020) (handled by manual parsing and ApproxDate)

    # pass on already parsed dates
    if isinstance(v, ApproxDate):
        return v

    if v is None:
        return None

    try:
        exact_date = datetime.fromisoformat(v).date()
        approx_date = ApproxDate(exact_date, exact_date, source_string=v)
        return approx_date
    except ValueError:
        try:
            approx_date = ApproxDate.from_iso8601(v)
            return approx_date
        except ValueError:
            # two partial dates split by " to "
            # short iso to short iso
            date_strings = v.split(" to ")
            if len(date_strings) != 2:
                raise ValueError(f'Could not find two iso dates split by "to" in {v}')
            early_date, late_date = map(date.fromisoformat, date_strings)
            approx_date = ApproxDate(early_date, late_date, source_string=v)
            return approx_date


class Performance(BaseModel):
    name: NonEmptyStr
    date: Annotated[Optional[ApproxDate], BeforeValidator(parse_date)]
    cast: Mapping[NonEmptyStr, NonEmptyStrList]
    leading_team: Mapping[NonEmptyStr, NonEmptyStrList]
    stage: NonEmptyStr
    production: NonEmptyStr
    composer: NonEmptyStr
    comments: str
    is_concertante: bool
    production_id: Optional[int] = Field(default=None)
    key: PerformanceKey = Field(default_factory=create_key_for_visited_performance_v3)

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
        json_encoders={ApproxDate: str},
        frozen=True,
    )


def is_exact_date(date: ApproxDate | None) -> bool:
    return date is not None and date.earliest_date == date.latest_date


DB_TYPE = Sequence[Performance]


def normalize_title(title: str) -> str:
    return "".join(
        filter(
            str.isalpha,
            unidecode(title)
            .split("(")[0]
            .split("/")[0]
            .lower()
            .replace(" ", "")
            .strip(),
        )
    )


def get_all_names_from_performance(performance: Performance) -> set[str]:
    return_set = set(
        flatten(
            ChainMap(
                performance.leading_team,
                performance.cast,
            ).values()
        )
    )

    if performance.composer != "":
        return_set.add(performance.composer)

    return return_set


def filter_only_full_entries(db: DB_TYPE) -> DB_TYPE:
    db_filtered = [
        performance
        for performance in db
        if (len(performance.cast) + len(performance.leading_team)) > 0
    ]

    return db_filtered


T = TypeVar("T")


def soft_isinstance(obj: Any, type_: type[T]) -> TypeGuard[T]:
    # hacky way to check if the type is type_ since
    # st rerun mechanism does not work with isinstance
    # of pydantic models

    return obj.__class__.__name__ == type_.__name__


def is_performance_instance(obj: Any) -> TypeGuard[Performance]:
    return soft_isinstance(obj, Performance)


class WorkYearEntryModel(BaseModel):
    composer: NonEmptyStr
    title: NonEmptyStr
    year: int
    key: DetaKey = Field(default_factory=create_deta_style_key)

    model_config = ConfigDict(frozen=True, validate_default=True)


class VenueModel(BaseModel):
    name: NonEmptyStr
    short_name: NonEmptyStr
    key: DetaKey = Field(default_factory=create_deta_style_key)

    model_config = ConfigDict(frozen=True, validate_default=True)


PASS_HASH = PasswordHasher()


def hash_password_if_needed(password: str) -> str:
    if password.startswith("$argon2"):
        # already hashed
        return password

    return PASS_HASH.hash(password)


class PasswordModel(BaseModel):
    key: DetaKey = Field(default_factory=create_deta_style_key)
    password: Annotated[str, AfterValidator(hash_password_if_needed)]

    model_config = ConfigDict(frozen=True, validate_default=True)

    def verify_password(self, password: str):
        try:
            return PASS_HASH.verify(self.password, password)
        except VerifyMismatchError:
            return False


if __name__ == "__main__":
    # test the key creation
    print(PasswordModel(password="password"))
