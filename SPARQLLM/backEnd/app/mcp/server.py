from dotenv import load_dotenv
load_dotenv()

from mcp_instance import mcp
import tools  
import resources 

if __name__ == "__main__":
    mcp.run()  