#!/usr/bin/env python3
import os
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom

def calculate_type_encoding(return_type, selector, params=None):
    # Map _Bool to bool for consistency
    if return_type == '_Bool':
        return_type = 'bool'
    
    # Special method signatures with known encodings
    special_method_encodings = {
        # Memory management methods
        'dealloc': 'v16@0:8',  # -(void) dealloc
        'release': 'v16@0:8',  # -(void) release
        'retain': '@16@0:8',   # -(id) retain
        'autorelease': '@16@0:8', # -(id) autorelease
        
        # Initialization methods
        'init': '@16@0:8',     # -(id) init
        'new': '@16@0:8',      # +(id) new
        'alloc': '@16@0:8',    # +(id) alloc
        
        # Comparison and equality methods
        'isEqual:': 'B24@0:8@16',  # -(BOOL) isEqual:(id)
        'isLogFile:': 'B24@0:8@16',  # -(BOOL) isLogFile:(id)
        'isInSet:': 'B24@0:8@16',  # -(BOOL) isInSet:(id)
        'hash': 'Q16@0:8',     # -(NSUInteger) hash
        
        # Description methods
        'description': '@16@0:8',  # -(NSString *) description
        'debugDescription': '@16@0:8',  # -(NSString *) debugDescription
        
        # Class/type methods
        'class': '#16@0:8',    # +(Class) class
        'superclass': '#16@0:8',  # +(Class) superclass
        'conformsToProtocol:': 'B24@0:8^#16',  # -(BOOL) conformsToProtocol:(Protocol *)
        'isKindOfClass:': 'B24@0:8#16',  # -(BOOL) isKindOfClass:(Class)
        'respondsToSelector:': 'B24@0:8:16',  # -(BOOL) respondsToSelector:(SEL)
        
        # Copying methods
        'copyWithZone:': '@24@0:8^{_NSZone=}16',  # -(id) copyWithZone:(NSZone *)
        'mutableCopyWithZone:': '@24@0:8^{_NSZone=}16'  # -(id) mutableCopyWithZone:(NSZone *)
    }
    
    if selector in special_method_encodings:
        return special_method_encodings[selector]
    
    # Handle BOOL methods with id parameter
    if return_type.strip() in ['BOOL', '_Bool'] and ':' in selector:
        param_type = selector.split(':')[1].strip()
        if param_type == '(id)':
            return 'B24@0:8@16'
    
    # Handle instancetype at the encoding level
    if return_type.strip() == 'instancetype':
        return_type = 'id'
    
    params_count = selector.count(':')
    base_size = 16
    param_size = 8
    total_size = base_size + (param_size * params_count)
    return_type = return_type.strip()
    
    # Handle completion handlers and block types
    if '^' in return_type or 'CDUnknownBlockType' in return_type:
        # Handle completion handler with BOOL parameter
        if '(void (^)(_Bool))' in return_type or '(void (^)(BOOL))' in return_type:
            return f"v32@0:8@?16@24"  # void return, block with BOOL param
        # Handle completion handler with void parameter
        elif '(void (^)(void))' in return_type:
            return f"v24@0:8@?16"  # void return, block with void param
        # Handle completion handler with id parameter
        elif '(void (^)(id))' in return_type:
            return f"v32@0:8@?16@24"  # void return, block with id param
        # Handle block as parameter
        elif 'CDUnknownBlockType' in return_type:
            return f"v32@0:8@?16@24"  # void return with block parameter
        # Handle block returning BOOL
        elif return_type.startswith('_Bool (^)') or return_type.startswith('BOOL (^)'):
            return f"B32@0:8@?16@24"  # BOOL return with block
        else:
            return f"@32@0:8@?16@24"  # generic block type
    
    # Handle struct types
    struct_types = {
        "CGRect": "{CGRect={CGPoint=dd}{CGSize=dd}}",
        "CGPoint": "{CGPoint=dd}",
        "CGSize": "{CGSize=dd}",
        "NSRange": "{_NSRange=QQ}",
        "UIEdgeInsets": "{UIEdgeInsets=dddd}",
        "CGAffineTransform": "{CGAffineTransform=dddddd}",
        "IMAAdPlaybackInfo": "^{?=iiiiddddd{?=iiiiiiiiiiiiii}}",
        "struct _NSZone *": "^{_NSZone=}",
        "_NSZone *": "^{_NSZone=}",
        "NSXMLParser *": "@",
        "Protocol *": "^#",
        "id<Protocol>": "@"
    }
    
    if return_type in struct_types:
        type_prefix = struct_types[return_type]
        return f"{type_prefix}{total_size}@0:8"
    
    # Basic type mapping
    type_map = {
        "void": "v",
        "BOOL": "B", "bool": "B", "_Bool": "B", "Bool": "B", "bool_": "B",
        "instancetype": "@",  # Map instancetype to id encoding
        "double": "d",
        "long long": "q", "long": "q",
        "unsigned long long": "Q",
        "unsigned int": "I",
        "int": "i",
        "float": "f",
        "id": "@",
        "NSString *": "@",
        "NSArray *": "@",
        "NSDictionary *": "@",
        "NSObject *": "@",
        "Class": "#",
        "SEL": ":",
        "char *": "*",
        "const char *": "r*",
        "void *": "^v",
        "IMP": "^?",
        "id *": "^@",
        "NSError *": "@",
        "NSError **": "^@",
        "CDUnknownBlockType": "@?",
        "dispatch_block_t": "@?",
        "void(^)(void)": "@?"
    }
    
    # Handle pointer types more robustly
    if return_type.endswith('**'):
        base_type = return_type.rstrip('* ').strip()
        # Handle const for double pointers
        if 'const' in base_type:
            base_type = base_type.replace('const', '').strip()
            if base_type.startswith('NS') or base_type.startswith('UI'):
                type_prefix = "r^@"  # const pointer to NS/UI object pointer
            else:
                type_prefix = "r^^"  # const pointer to pointer
        else:
            if base_type.startswith('NS') or base_type.startswith('UI'):
                type_prefix = "^@"  # pointer to NS/UI object pointer
            else:
                type_prefix = "^^"  # pointer to pointer
    elif return_type.endswith('*'):
        base_type = return_type.rstrip('* ').strip()
        # Handle const for single pointers
        if 'const' in base_type:
            base_type = base_type.replace('const', '').strip()
            if base_type.startswith('NS') or base_type.startswith('UI'):
                type_prefix = "r@"  # const NS/UI object pointer
            elif base_type == "char":
                type_prefix = "r*"  # const char pointer
            else:
                type_prefix = "r^"  # const pointer
        else:
            if base_type.startswith('NS') or base_type.startswith('UI'):
                type_prefix = "@"  # NS/UI object pointer
            else:
                type_prefix = "^"  # regular pointer
    else:
        type_prefix = type_map.get(return_type, '@')
    
    return f"{type_prefix}{total_size}@0:8"

def process_header_file(file_path):
    methods = []
    current_interface = None
    current_category = None
    superclass = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Remove comments and preprocessor directives
        content = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'#.*?\n', '', content)
        
        # Better multi-line method handling
        content = re.sub(r'(\n\s*)([+-])', r' \2', content)  # Preserve method declarations
        
        # Improved interface/protocol/category detection
        interface_match = re.search(r'@interface\s+(\w+)\s*:\s*(\w+)', content)
        protocol_match = re.search(r'@protocol\s+(\w+)', content)
        category_match = re.search(r'@interface\s+(\w+)\s*\((\w*)\)', content)
        
        if interface_match:
            current_interface = interface_match.group(1)
            superclass = interface_match.group(2)
        elif protocol_match:
            current_interface = protocol_match.group(1)
            superclass = "NSObject"  # Protocols inherit from NSObject
        elif category_match:
            current_interface = category_match.group(1)
            superclass = None  # Categories don't define superclasses
        
        # Default to NSObject if no class found
        if not current_interface:
            current_interface = "NSObject"
        
        # Extract all method declarations
        method_pattern = r'([+-])\s*\(([\w\s*<>{}\[\]]+(?:\s*\*)?)\)\s*([^;]+);'
        method_matches = re.finditer(method_pattern, content)
        
        seen_methods = set()
        
        for match in method_matches:
            prefix, return_type, selector = match.groups()
            
            # Clean up selector (handle multi-line)
            selector = re.sub(r'\s+', ' ', selector.strip())
            
            # Create unique key for method
            method_key = f"{prefix}{selector.strip()}"
            if method_key in seen_methods:
                continue
            seen_methods.add(method_key)
            
            method_info = parse_method_declaration(f"{prefix}({return_type}) {selector}", current_interface)
            if method_info:
                method_info['className'] = current_interface
                methods.append(method_info)
        
        return methods, current_interface, superclass
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return [], None, None

def parse_method_declaration(line, class_name):
    # Extract method components with improved regex to handle all parameters
    match = re.match(r'^([+-])\s*\(([\w\s*<>]+)\)\s*((?:[^\s:]+\s*(?:\([^)]+\))?\s*:?\s*(?:\([^)]+\))?\s*)*)', line)
    if not match:
        return None
        
    prefix, return_type, selector_with_types = match.groups()
    
    # Clean up return type and handle _Bool
    return_type = return_type.strip()
    if return_type == '_Bool':
        return_type = 'bool'
    
    # Parse selector and parameters - improved to catch all arguments
    parts = []
    current_pos = 0
    method_parts = selector_with_types.split(':')
    
    if ':' not in selector_with_types:
        # Handle methods without parameters
        selector = selector_with_types.strip()
        display_name = f"{prefix}({return_type}) {selector}"
    else:
        # Parse each parameter section
        method_name = method_parts[0].strip()
        param_sections = re.finditer(r'(\w+)?\s*:\s*\(([^)]+)\)', selector_with_types)
        
        selector_parts = []
        display_parts = []
        
        for match in param_sections:
            param_name = match.group(1) or ''
            param_type = match.group(2).strip()
            
            # Clean parameter type
            if param_type == '_Bool':
                param_type = 'bool'
            elif param_type.lower() in ['id', 'id)', 'instancetype']:
                param_type = 'id'
                
            if param_name:
                selector_parts.append(f"{param_name}:")
                display_parts.append(f"{param_name}:({param_type})")
            else:
                selector_parts.append(":")
                display_parts.append(f":({param_type})")
            
            parts.append((param_name, param_type))
        
        if method_name:
            selector = method_name + ':' + ''.join(selector_parts)
            display_name = f"{prefix}({return_type}) {method_name}:" + ' '.join(display_parts)
        else:
            selector = ''.join(selector_parts)
            display_name = f"{prefix}({return_type}) " + ' '.join(display_parts)

    # Calculate type encoding
    type_encoding = calculate_type_encoding(return_type, selector, parts)
    
    return {
        'prefix': prefix,
        'selector': selector,
        'typeEncoding': type_encoding,
        'displayName': display_name,
        'className': class_name
    }

def clean_method_name(name):
    """Thoroughly clean method names"""
    name = name.strip()
    name = re.sub(r'\s*arg\d+\s*', '', name)  # Remove all argN
    name = re.sub(r'\s+', ' ', name)  # Clean up spaces
    return name

def clean_parameter_type(param_type):
    """Thoroughly clean parameter types"""
    if not param_type:
        return 'id'
        
    param_type = param_type.strip('() ')
    param_type = re.sub(r'_Bool\s*\)?', 'bool', param_type, flags=re.IGNORECASE)
    param_type = re.sub(r'BOOL\s*\)?', 'bool', param_type, flags=re.IGNORECASE)
    param_type = re.sub(r'\s*\)\s*$', '', param_type)
    param_type = re.sub(r'\s+', ' ', param_type)
    
    if param_type.lower() in ['id)', 'id']:
        return 'id'
        
    return param_type

def parse_method_parts(selector):
    """Parse method parts with improved cleaning"""
    parts = []
    current_name = []
    current_type = []
    in_parens = 0
    
    tokens = re.findall(r'[^:\s()]+|\(|\)|:', selector)
    
    for token in tokens:
        if token == '(':
            in_parens += 1
            if in_parens == 1:
                continue
        elif token == ')':
            in_parens -= 1
            if in_parens == 0:
                continue
        elif token == ':':
            if in_parens == 0:
                name = ''.join(current_name).strip()
                param_type = ''.join(current_type).strip()
                parts.append((name, param_type))
                current_name = []
                current_type = []
                continue
                
        if in_parens > 0:
            current_type.append(token)
        else:
            current_name.append(token)
            
    return parts

def format_parameter(param_type):
    # Add thorough parameter cleaning
    param_type = param_type.strip('() ')
    param_type = re.sub(r'_Bool\s*\)?', 'bool', param_type, flags=re.IGNORECASE)
    param_type = re.sub(r'BOOL\s*\)?', 'bool', param_type, flags=re.IGNORECASE)
    param_type = re.sub(r'\s*\)\s*$', '', param_type)  # Remove trailing )
    param_type = re.sub(r'\s+', ' ', param_type)  # Clean up spaces
    return param_type

def clean_type(type_str):
    """Clean up type declarations to match Flex 3 format exactly"""
    # Remove extra spaces and parentheses
    type_str = type_str.strip('() ')
    
    # Handle instancetype explicitly
    if type_str == 'instancetype':
        return 'id'
    
    # Handle boolean types
    if type_str.lower() in ['_bool', 'bool', 'bool_', 'bool', 'BOOL']:
        return 'bool'
    
    # Handle id types
    if type_str.lower() in ['id)', 'id']:
        return 'id'
    
    # Handle numeric types
    if type_str == 'double':
        return 'double'
    if type_str == 'float':
        return 'float'
    if type_str == 'int':
        return 'int'
    
    # Handle common Objective-C types
    type_map = {
        'void': 'void',
        'NSString *': 'NSString *',
        'NSArray *': 'NSArray *',
        'NSDictionary *': 'NSDictionary *',
        'NSObject *': 'NSObject *',
        'NSError *': 'NSError *',
        'Class': 'Class',
        'SEL': 'SEL',
        'CGRect': 'struct CGRect',
        'CGPoint': 'struct CGPoint',
        'CGSize': 'struct CGSize'
    }
    
    # Need more aggressive cleaning
    type_str = re.sub(r'\s*\)$', '', type_str)  # Remove trailing )
    type_str = re.sub(r'_Bool\s*\)?', 'bool', type_str, flags=re.IGNORECASE)
    type_str = re.sub(r'BOOL\s*\)?', 'bool', type_str, flags=re.IGNORECASE)
    
    return type_map.get(type_str, type_str)

def create_extracted_xml(framework_name, headers_dir):
    root = ET.Element("plist", version="1.0")
    dict_root = ET.SubElement(root, "dict")
    
    # Add classes key and array
    classes_key = ET.SubElement(dict_root, "key")
    classes_key.text = "objcClasses"
    array_classes = ET.SubElement(dict_root, "array")
    
    # Process headers and create class data
    classes_data = []
    for filename in sorted(os.listdir(headers_dir)):
        if not filename.endswith('.h'):
            continue
            
        filepath = os.path.join(headers_dir, filename)
        methods, class_name, super_class = process_header_file(filepath)
        
        if methods:  # Only add if we have valid methods
            class_info = {
                'name': class_name,
                'superClassName': super_class,
                'methods': methods
            }
            classes_data.append(class_info)
    
    # Create XML structure
    for class_info in classes_data:
        dict_class = ET.SubElement(array_classes, "dict")
        
        # Add methods array
        methods_key = ET.SubElement(dict_class, "key")
        methods_key.text = "methods"
        methods_array = ET.SubElement(dict_class, "array")
        
        for method in class_info['methods']:
            method_dict = ET.SubElement(methods_array, "dict")
            
            # Clean method info to remove any remaining arg1, arg2
            clean_method = {
                'className': method['className'],
                'displayName': method['displayName'].replace('arg1', '').replace('arg2', '').replace('arg3', '').replace('arg4', ''),
                'prefix': method['prefix'],
                'selector': method['selector'].replace('arg1', '').replace('arg2', '').replace('arg3', '').replace('arg4', ''),
                'typeEncoding': method['typeEncoding']
            }
            
            # Add method info exactly matching Flex format
            for key in ["className", "displayName", "prefix", "selector", "typeEncoding"]:
                key_elem = ET.SubElement(method_dict, "key")
                key_elem.text = key
                string_elem = ET.SubElement(method_dict, "string")
                string_elem.text = clean_method[key]
        
        # Add class name
        ET.SubElement(dict_class, "key").text = "name"
        ET.SubElement(dict_class, "string").text = class_info['name']
        
        # Only add superclass if it exists (not for categories)
        if class_info.get('superClassName'):
            ET.SubElement(dict_class, "key").text = "superClassName"
            ET.SubElement(dict_class, "string").text = class_info['superClassName']
    
    ET.SubElement(dict_root, "key").text = "version"
    ET.SubElement(dict_root, "real").text = "1.2050000429153442"
    
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="\t")
    xmlstr = '\n'.join(line for line in xmlstr.split('\n') if line.strip())
    
    output_file = f"{framework_name}.extracted"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n')
        plist_content = xmlstr[xmlstr.find('<plist'):]
        f.write(plist_content)
    
    print(f"Successfully created {output_file}")

def main():
    framework_name = input("Enter framework name (without extension): ")
    headers_dir = input("Enter path to headers directory: ")
    headers_dir = os.path.abspath(headers_dir)
    
    if not os.path.isdir(headers_dir):
        print(f"Error: '{headers_dir}' is not a valid directory")
        return
    
    create_extracted_xml(framework_name, headers_dir)

if __name__ == "__main__":
    main()