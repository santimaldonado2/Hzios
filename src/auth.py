import yaml
from streamlit_authenticator import Authenticate

def auth():
    with open('./config/config.yaml') as file:
        config = yaml.load(file, Loader=yaml.SafeLoader)

    authenticator = Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    authenticator.login('Hzios', 'main')
    return(authenticator)

