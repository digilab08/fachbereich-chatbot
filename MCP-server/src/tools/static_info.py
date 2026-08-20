import csv
import io

from fastmcp import FastMCP
from services.study_programs_svc import study_program_exists, list_study_programs
from services.contact_point_svc import get_contact_points_by_degree_program

def register_static_info_tools(mcp: FastMCP) -> None:
    """
    Register static information tools on the given FastMCP server instance.
    
    :param mcp: The FastMCP server instance.
    """
    
    @mcp.tool()
    async def list_all_study_programs() -> str:
        """
        Returns study program abbreviations and full names as CSV-formatted text.
        
        :return: A formatted string listing all study programs.
        """
        
        
        programs = list_study_programs()
        if not programs:
            return "Error: No study programs found."

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["abbreviation", "full name"])
        for program in programs:
            abbreviation = program.get("abbreviation", "N/A")
            full_name = program.get("full name", "N/A")
            writer.writerow([abbreviation, full_name])

        return output.getvalue()

    @mcp.tool()
    async def get_contact_points(degree_program_abbreviation: str | None = None) -> str:
        """
        Returns contact points for the specified degree program code as CSV-formatted text.
        
        :param degree_program_abbreviation: The code for the degree program to filter by. If None, returns all contact points.
        :return: A formatted string listing contact points.
        """
        if not study_program_exists(degree_program_abbreviation):
            return f"Error: The degree program code '{degree_program_abbreviation}' is not recognized. Probably use another tool to check which programs are available or ask the user for clarification."

        contact_points = get_contact_points_by_degree_program(degree_program_abbreviation)

        if not contact_points:
            return ""

        fieldnames = list(contact_points[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(contact_points)

        return output.getvalue()
        