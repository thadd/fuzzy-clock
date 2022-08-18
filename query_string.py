def parse(body):
    parameters = {}

    param_split = body.split("&")
     
    for param in param_split:
        equal_split = param.split("=")

        # Restore ampersands and question marks, etc
        val = equal_split[1]
        val = val.replace('%24', '$').replace('%24', '$')
        val = val.replace('%26', '&').replace('%26', '&')
        val = val.replace('%2B', '+').replace('%2b', '+')
        val = val.replace('%2C', ',').replace('%2c', ',')
        val = val.replace('%2E', '.').replace('%2e', '.')
        val = val.replace('%2F', '/').replace('%2f', '/')
        val = val.replace('%27', '\'').replace('%27', '\'')
        val = val.replace('%22', '"').replace('%22', '"')
        val = val.replace('%3A', ':').replace('%3a', ':')
        val = val.replace('%3B', ';').replace('%3b', ';')
        val = val.replace('%3D', '=').replace('%3d', '=')
        val = val.replace('%3F', '?').replace('%3f', '?')
        val = val.replace('%40', '@').replace('%40', '@')
        val = val.replace('%3C', '<').replace('%3c', '<')
        val = val.replace('%3E', '>').replace('%3e', '>')
        val = val.replace('%23', '#').replace('%23', '#')
        val = val.replace('%25', '%').replace('%25', '%')
        val = val.replace('%7B', '{').replace('%7b', '{')
        val = val.replace('%7D', '}').replace('%7d', '}')
        val = val.replace('%7C', '|').replace('%7c', '|')
        val = val.replace('%5C', '\\').replace('%5c', '\\')
        val = val.replace('%5E', '^').replace('%5e', '^')
        val = val.replace('%7E', '~').replace('%7e', '~')
        val = val.replace('%5B', '[').replace('%5b', '[')
        val = val.replace('%5D', ']').replace('%5d', ']')
        val = val.replace('%60', '`').replace('%60', '`')
        val = val.replace('%20', ' ').replace('%20', ' ')
        val = val.replace('%21', '!').replace('%21', '!')

        # Store to the dictionary
        parameters[equal_split[0]] = val

    return parameters