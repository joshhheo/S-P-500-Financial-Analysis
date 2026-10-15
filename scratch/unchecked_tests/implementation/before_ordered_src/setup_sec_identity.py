import os
from dotenv import load_dotenv
from edgar import set_identity

def setup_sec_identity():
    # writes environment variables to os environment
    load_dotenv()
    # accesses variable from os environment
    user_agent = os.getenv("SEC_user_agent")
    set_identity(user_agent)
