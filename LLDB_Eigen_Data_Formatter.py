import lldb
import os
import re



def __lldb_init_module (debugger, dict):
    debugger.HandleCommand("type summary add -x \"Eigen::Matrix\" -F LLDB_Eigen_Data_Formatter.format_matrix")
    debugger.HandleCommand("type summary add -x \"Eigen::Array\" -F LLDB_Eigen_Data_Formatter.format_matrix")

# Define a context manager to suppress stdout and stderr.
#  see http://stackoverflow.com/questions/11130156/suppress-stdout-stderr-print-from-python-functions
class suppress_stdout_stderr(object):
    def __init__(self):
        # Open a pair of null files
        self.null_fds =  [os.open(os.devnull,os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0],1)
        os.dup2(self.null_fds[1],2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0],1)
        os.dup2(self.save_fds[1],2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])


# Somewhat nasty way to determine if a matrix is row-major or column-major.
def extract_is_row_major(matrix_var):
    """
    Determines if an Eigen matrix is row-major based on its type signature.
    :param matrix_var: LLDB SBValue representing the Eigen matrix variable.
    :return: True if row-major, False if column-major, None if the type couldn't be parsed.
    """
    matrix_type = matrix_var.GetType().GetName()
    
    # Use regex to extract the template parameters from the type string
    template_regex = re.compile(r'Eigen::Matrix<[^,]+, [^,]+, [^,]+, (\d),')
    match = template_regex.search(matrix_type)
    
    if not match:
        print("Could not determine matrix layout from type:", matrix_type)
        return None

    # The fourth template argument (1 for row-major, 0 for column-major)
    storage_order = match.group(1)
    
    if storage_order == '1':
        return True
    elif storage_order == '0':
        return False
    else:
        print("Unexpected storage order value:", storage_order)
        return None


def evaluate_expression(valobj, expr):
    return valobj.GetProcess().GetSelectedThread().GetSelectedFrame().EvaluateExpression(expr)


def _row_element(valobj, row, rows, cols, is_row_major):
    if is_row_major:
        for i in range(row*cols, (row+1)*cols):
            yield valobj.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValue()
    else:
        for i in range(row, rows*cols, rows):
            yield valobj.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValue()


def print_raw_matrix(valobj, rows, cols, is_row_major):
    if rows*cols > 100:
      return "[matrix too large]"
    output = ""
    # print matrix dimensions
    output += f"rows: {rows}, cols: {cols}, is_row_major: {is_row_major}\n["

    # determine padding
    padding = 1
    for i in range(0, rows*cols):
        padding = max(padding, len(str(valobj.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValue())))

    # print values
    for j in range(0, rows):
        if j!=0:
            output += " "

        output += "".join(val.rjust(padding+1, ' ') for val in _row_element(valobj, j, rows, cols, is_row_major)) + ";\n"
        
    return output + " ]\n"

def fixed_sized_matrix_to_string(valobj):
    data = valobj.GetValueForExpressionPath(".m_storage.m_data.array")
    num_data_elements = data.GetNumChildren()

    # return usual summary if storage can not be accessed
    if not data.IsValid():
        return valobj.GetSummary()

    # determine expression path of the current valobj
    stream = lldb.SBStream()
    valobj.GetExpressionPath(stream)
    valobj_expression_path = stream.GetData()

    # determine rows and cols
    rows = cols = 0
    with suppress_stdout_stderr():
        # todo: check result is valid
        rows = evaluate_expression(valobj, valobj_expression_path+".rows()").GetValueAsSigned()
        cols = evaluate_expression(valobj, valobj_expression_path+".cols()").GetValueAsSigned()
        #rows = lldb.frame.EvaluateExpression(valobj_expression_path+".rows()").GetValueAsSigned()
        #cols = lldb.frame.EvaluateExpression(valobj_expression_path+".cols()").GetValueAsSigned()

    #print(valobj.CreateValueFromExpression("bla", valobj_expression_path+".rows()"))

    # check that the data layout fits a regular dense matrix
    if rows*cols != num_data_elements:
      print("error: eigen data formatter: could not infer data layout. printing raw data instead")
      cols = 1
      rows = num_data_elements
    
    return print_raw_matrix(data, rows, cols, extract_is_row_major(valobj))

def dynamically_sized_matrix_to_string(valobj):
    data = valobj.GetValueForExpressionPath(".m_storage.m_data")
    num_data_elements = data.GetNumChildren()

    # return usual summary if storage can not be accessed
    if not data.IsValid():
        return valobj.GetSummary()

    # determine expression path of the current valobj
    stream = lldb.SBStream()
    valobj.GetExpressionPath(stream)
    valobj_expression_path = stream.GetData()

    # determine rows and cols
    rows = cols = 0
    with suppress_stdout_stderr():
        # todo: check result is valid
        rows = evaluate_expression(valobj, valobj_expression_path+".rows()").GetValueAsSigned()
        cols = evaluate_expression(valobj, valobj_expression_path+".cols()").GetValueAsSigned()

    # try to access last value (if this throws an exception the matrix is probably not declared yet)
    memory_accessable = True
    try:
        valobj.GetChildAtIndex(rows*cols, lldb.eNoDynamicValues, True).GetValue()
    except:
        memory_accessable = False

    if not memory_accessable:
        return "[uninitialized]"

    return print_raw_matrix(data, rows, cols, extract_is_row_major(valobj))

def format_matrix(valobj,internal_dict):
    # determine type
    if valobj.GetValueForExpressionPath(".m_storage.m_data.array").IsValid():
        return fixed_sized_matrix_to_string(valobj)
    elif valobj.GetValueForExpressionPath(".m_storage.m_data").GetType().IsPointerType():
        return dynamically_sized_matrix_to_string(valobj)
    else:
        return valobj.GetSummary()
