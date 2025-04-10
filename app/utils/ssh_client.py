import paramiko
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SSHConfig(BaseModel):
    hostname: str
    port: int = 22
    username: str
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 10

class SSHClient:
    def __init__(self, config: SSHConfig):
        self.config = config
        self.client = None
    
    def connect(self) -> bool:
        """
        Establishes SSH connection
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.config.hostname,
                "port": self.config.port,
                "username": self.config.username,
                "timeout": self.config.timeout
            }
            
            if self.config.password:
                connect_kwargs["password"] = self.config.password
            if self.config.key_filename:
                connect_kwargs["key_filename"] = self.config.key_filename
            
            self.client.connect(**connect_kwargs)
            logger.info(f"Successfully connected to {self.config.hostname}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.hostname}: {str(e)}")
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Executes command on the remote server
        """
        if not self.client:
            if not self.connect():
                return {"success": False, "message": "Failed to connect to server"}
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            return {
                "success": exit_status == 0,
                "output": output,
                "error": error,
                "exit_status": exit_status
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def check_ufw_status(self) -> Dict[str, Any]:
        """
        Checks UFW status
        """
        # Check if UFW is installed
        check_ufw = self.execute_command("which ufw")
        if not check_ufw["success"]:
            return {
                "status": "not_available",
                "message": "UFW is not installed on the server"
            }
        
        # Get UFW status
        status = self.execute_command("ufw status")
        if not status["success"]:
            return {
                "status": "error",
                "message": f"Failed to get UFW status: {status['error']}"
            }
        
        # Parse output
        output = status["output"].lower()
        if "active" in output:
            return {
                "status": "active",
                "message": "UFW is active",
                "rules": self.get_ufw_rules()
            }
        else:
            return {
                "status": "inactive",
                "message": "UFW is inactive"
            }
    
    def get_ufw_rules(self) -> Dict[str, Any]:
        """
        Gets UFW rules list in structured format
        """
        rules_cmd = self.execute_command("ufw status numbered")
        if not rules_cmd["success"]:
            return {"success": False, "message": f"Failed to get rules: {rules_cmd['error']}"}

        raw_output = rules_cmd["output"]
        structured_rules = {}

        result = {
            "success": True,
            "raw_output": raw_output,
            "rules": {}
        }

        lines = raw_output.split("\n")
        start_index = -1
        for i, line in enumerate(lines):
            # Find header line to start parsing after it
            if line.strip().startswith("To") and "Action" in line and "From" in line:
                 # Consider possible header variations, such as 'Status: active' before the table
                if i + 1 < len(lines) and lines[i+1].strip().startswith("---"): # Look for separator ---
                    start_index = i + 2 # Rules start after the separator
                    break
                else: # If no separator, assume rules start right after the header
                    start_index = i + 1
                    break
            elif line.strip().startswith("["): # If no headers but rule lines exist
                 start_index = i
                 break


        if start_index == -1:
             # If no rules (or couldn't find the starting point), return success but empty rules
             if "Status: inactive" in raw_output:
                 result["message"] = "UFW is inactive, no rules."
             elif "Status: active" in raw_output:
                  result["message"] = "UFW is active, but no user rules found."
             else:
                 result["message"] = "Could not parse rule format or no rules found."
             result["rules"] = {}
             result["count"] = 0
             return result

        # Parse each rule line
        for line in lines[start_index:]:
            line = line.strip()
            if not line:
                continue

            # Look for rule number in format [ X] or [XX]
            if not line.startswith("[") or "]" not in line:
                continue

            try:
                rule_match = line.split("]", 1)
                rule_number = int(rule_match[0].replace("[", "").strip())
                rule_detail_str = rule_match[1].strip()
                rule_parts = rule_detail_str.split()

                # Initialize variables
                port_protocol = ""
                action = "PARSE_ERROR"
                direction = ""
                source = ""
                is_ipv6 = False
                port = ""
                protocol = ""

                if len(rule_parts) >= 3:  # Minimum for port/proto, action, direction
                    port_protocol = rule_parts[0]

                    # Check for IPv6 marker - can be after the port or as the next element
                    offset = 0
                    if "(v6)" in port_protocol:
                         is_ipv6 = True
                         port_protocol = port_protocol.replace("(v6)", "").strip() # Remove the marker
                         action = rule_parts[1]
                         direction = rule_parts[2]
                         source = " ".join(rule_parts[3:])
                    elif rule_parts[1] == "(v6)":
                        is_ipv6 = True
                        offset = 1 # Shift index for action, direction, source
                        action = rule_parts[1 + offset]
                        direction = rule_parts[2 + offset]
                        source = " ".join(rule_parts[3 + offset:])
                    else:
                        # Assume IPv4
                        is_ipv6 = False
                        action = rule_parts[1]
                        direction = rule_parts[2]
                        source = " ".join(rule_parts[3:])

                    # Split port/protocol
                    if "/" in port_protocol:
                        port_parts = port_protocol.split("/", 1)
                        port = port_parts[0]
                        protocol = port_parts[1]
                    else:
                        port = port_protocol # Could be 'Anywhere' or just a port without protocol

                # Create structured rule if parsing succeeded
                if action != "PARSE_ERROR":
                    structured_rules[rule_number] = {
                        "port": port,
                        "protocol": protocol,
                        "port_protocol": rule_parts[0], # Save original for reference
                        "action": action,
                        "direction": direction,
                        "source": source,
                        "is_ipv6": is_ipv6, # Add IPv6 flag
                        "raw": line
                    }
                else:
                     structured_rules[rule_number] = {"raw": line, "is_ipv6": "(v6)" in line, "error": "Failed to parse rule structure"}

            except ValueError:
                 logger.warning(f"Could not parse rule number from line: {line}")
                 structured_rules[f"parse_error_num_{len(structured_rules)}"] = {"raw": line, "error": "Could not parse rule number"}
            except IndexError:
                 logger.warning(f"Index error parsing rule line: {line}")
                 structured_rules[f"parse_error_idx_{len(structured_rules)}"] = {"raw": line, "error": "Index error during parsing"}
            except Exception as e:
                logger.error(f"Generic error parsing rule line '{line}': {str(e)}")
                structured_rules[f"parse_error_gen_{len(structured_rules)}"] = {
                    "raw": line,
                    "error": str(e)
                }

        result["rules"] = structured_rules
        result["count"] = len([k for k in structured_rules if isinstance(k, int)]) # Count only successfully parsed

        return result
    
    def add_ufw_rule(self, port: int, protocol: str = "tcp", action: str = "allow") -> Dict[str, Any]:
        """
        Adds rule to UFW
        """
        command = f"ufw {action} {port}/{protocol}"
        result = self.execute_command(command)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Rule added successfully: {command}"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to add rule: {result['error']}"
            }
    
    def delete_ufw_rule(self, rule_number: int) -> Dict[str, Any]:
        """
        Deletes rule from UFW by number
        """
        # Use -f parameter for non-interactive mode (without asking for confirmation)
        command = f"ufw --force delete {rule_number}"
        result = self.execute_command(command)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Rule {rule_number} deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete rule: {result['error']}"
            }
    
    def close(self):
        """
        Closes SSH connection
        """
        if self.client:
            self.client.close()
            logger.info("SSH connection closed") 