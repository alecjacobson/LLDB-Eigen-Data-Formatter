import lldb
import os

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

def evaluate_expression(valobj, expr):
    return valobj.GetProcess().GetSelectedThread().GetSelectedFrame().EvaluateExpression(expr)


def _row_element(valobj, row, rows, cols):
    for i in range(row, rows*cols, rows):
        yield valobj.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValue()


def print_raw_matrix(valobj, rows, cols):
    if rows*cols > 100:
      return "[matrix too large]"
    output = ""
    # print matrix dimensions
    output += "rows: " + str(rows) + ", cols: " + str(cols) + "\n["

    # determine padding
    padding = 1
    for i in range(0, rows*cols):
        padding = max(padding, len(str(valobj.GetChildAtIndex(i, lldb.eNoDynamicValues, True).GetValue())))

    # print values
    for j in range(0, rows):
        if j!=0:
            output += " "

        output += "".join(val.rjust(padding+1, ' ') for val in _row_element(valobj, j, rows, cols)) + ";\n"
        
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
    
    return print_raw_matrix(data, rows, cols)

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

    return print_raw_matrix(data, rows, cols)

def format_matrix(valobj,internal_dict):
    # determine type
    if valobj.GetValueForExpressionPath(".m_storage.m_data.array").IsValid():
        return fixed_sized_matrix_to_string(valobj)
    elif valobj.GetValueForExpressionPath(".m_storage.m_data").GetType().IsPointerType():
        return dynamically_sized_matrix_to_string(valobj)
    else:
        return valobj.GetSummary()
