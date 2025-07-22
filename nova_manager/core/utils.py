def format_json_to_prompt(json_data):
    if not json_data:
        return "No data provided."

    def dict_to_str(d, indent=0):
        result = ""
        for key, value in d.items():
            result += "  " * indent + f"- {key}: "
            if isinstance(value, dict):
                result += "\n" + dict_to_str(value, indent + 1)
            elif isinstance(value, list):
                result += "\n" + list_to_str(value, indent + 1)
            else:
                result += str(value) + "\n"
        return result

    def list_to_str(lst, indent=0):
        result = ""
        for item in lst:
            if isinstance(item, dict):
                result += "\n" + dict_to_str(item, indent + 1)
            else:
                result += "  " * indent + f"- {item}\n"
        return result

    if isinstance(json_data, list):
        return list_to_str(json_data)

    return dict_to_str(json_data)
