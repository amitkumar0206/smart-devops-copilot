import configparser

def read_config():
    # Create a ConfigParser object that preserves case
    config = configparser.ConfigParser()
    config.optionxform = lambda optionstr: str(optionstr)  # This preserves the original case of keys

    # Read the configuration file
    config.read('config.ini')

    # Initialize an empty dictionary
    config_dict = {section: dict(config.items(section)) for section in config.sections()}

    return config_dict