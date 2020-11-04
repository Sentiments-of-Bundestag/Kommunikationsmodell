from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum

# is domain really needed?
# do we need to typecheck some documents?
# we get list of str from group 1, we have user & faction objects
# we send our own structure to group 2, so we dont need to validate?

# insert other enums/classes etc into here (like PoliticalFactions)


# member of german bundestag
class MDB(BaseModel):
    surname: str
    forename: str
    birthday: str
    title: Optional[str]
    speaker_id: Optional[str]
