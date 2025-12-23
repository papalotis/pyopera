import json
import random
import string
from collections import ChainMap, defaultdict
from datetime import date, datetime
from decimal import Decimal
from functools import total_ordering
from typing import (
    Annotated,
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Self,
    Sequence,
    TypeGuard,
    TypeVar,
)

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


@total_ordering
class ApproxDate(BaseModel):
    earliest_date: date
    latest_date: date

    def __lt__(self, other: Self) -> bool:
        if isinstance(other, date):
            return self.earliest_date < other

        return self.earliest_date < other.earliest_date


PerformanceKey = Annotated[SHA1Str, AfterValidator(key_create_creator(create_key_for_visited_performance_v3))]
DetaKey = Annotated[str, AfterValidator(key_create_creator(create_deta_style_key))]


class Performance(BaseModel):
    name: NonEmptyStr
    date: Optional[ApproxDate]
    cast: Mapping[NonEmptyStr, NonEmptyStrList]
    leading_team: Mapping[NonEmptyStr, NonEmptyStrList]
    stage: NonEmptyStr
    production: NonEmptyStr
    composer: NonEmptyStr
    comments: str
    is_concertante: bool
    archived: bool = False
    key: PerformanceKey = Field(default_factory=create_key_for_visited_performance_v3)
    day_index: Optional[int] = None
    visit_index: Optional[str] = None

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
        frozen=True,
    )

    @property
    def production_key(self) -> tuple[str, str, str, str]:
        identifying_person = self.production_identifying_person
        production = self.production
        name = self.name
        composer = self.composer

        return identifying_person, production, name, composer

    @property
    def production_identifying_person(self) -> str:
        leading_team = self.leading_team
        identifying_person_key = ["Musikalische Leitung", "Dirigent"] if self.is_concertante else ["Inszenierung"]
        for key in identifying_person_key:
            if key in leading_team:
                return leading_team[key][0]

        return ""


def is_exact_date(date: ApproxDate | None | dict) -> bool:
    if date is None:
        return False

    if isinstance(date, dict):
        date = ApproxDate(**date)

    return date.earliest_date == date.latest_date


DB_TYPE = Sequence[Performance]


def normalize_title(title: str) -> str:
    return "".join(
        filter(
            str.isalpha,
            unidecode(title).split("(")[0].split("/")[0].lower().replace(" ", "").strip(),
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
    db_filtered = [performance for performance in db if (len(performance.cast) + len(performance.leading_team)) > 0]

    return db_filtered


T = TypeVar("T")


def soft_isinstance(obj: Any, type_: type[T]) -> TypeGuard[T]:
    # hacky way to check if the type is type_ since
    # st rerun mechanism does not work with isinstance
    # of pydantic models

    return obj.__class__.__name__ == type_.__name__


def is_performance_instance(obj: Any) -> TypeGuard[Performance]:
    return soft_isinstance(obj, Performance)


def group_performances_by_visit(performances: Sequence[Performance]) -> dict[str, List[Performance]]:
    """
    Groups performances by their visit_index.
    Performances without a visit_index are treated as unique visits (keyed by their unique key).
    """
    visits = defaultdict(list)
    for p in performances:
        if p.visit_index is not None:
            visits[p.visit_index].append(p)
        else:
            # Use the performance key as the visit ID for standalone performances
            visits[p.key].append(p)
    return dict(visits)


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if plural is None:
        plural = singular + "s"

    return singular if count == 1 else plural


class WorkYearEntryModel(BaseModel):
    composer: NonEmptyStr
    title: NonEmptyStr
    year: int
    key: DetaKey = Field(default_factory=create_deta_style_key)

    model_config = ConfigDict(frozen=True, validate_default=True)


class VenueModel(BaseModel):
    name: NonEmptyStr
    short_name: NonEmptyStr
    longitude: Decimal | None = None
    latitude: Decimal | None = None
    key: DetaKey = Field(default_factory=create_deta_style_key)

    model_config = ConfigDict(frozen=True, validate_default=True)

    @property
    def longitude_float(self) -> float | None:
        return float(self.longitude) if self.longitude is not None else None

    @property
    def latitude_float(self) -> float | None:
        return float(self.latitude) if self.latitude is not None else None


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
