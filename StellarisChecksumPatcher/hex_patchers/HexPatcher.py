from . import *

def get_current_dir():
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(__file__)

    return application_path

class StellarisChecksumPatcher:
    APP_VERSION = ["d", 1, 0, 5]
    
    def __init__(self, dev=is_debug) -> None:
        self.hex_data_list = [] # Incoming original Hex data, so we can always have a copy of the original.
        self._hex_data_list_working = [] # Copy of original that will be taking the changes and be modified.

        self._dev = dev
        
        self.data_loaded = False

        self._manual_install_dir = ""
        
        self._chunk_char_len = 32 # Each line is comprised of 32 characters. Will need this to recompile from changed chunks back to binary
        
        self._hex_begin_static = ["48", "8B", "12"] # The Hex block begins with these values, so we can reference them.
        self._hex_end_static = ["85", "C0"] # The predicted end Hex values of the block.
        self._hex_end_change_to = ["33", "C0"] # Change the target ending Hexes of the block to this
        self._hex_wildcards_in_between = 14 # Up to 14 possible values to reach the predicted target end Hex
        
        self._checksum_block = []
        self._checksum_offset_start = 0
        self._checksum_offset_end = 0
        
        self.title_name = "Stellaris" # Steam title name
        self.exe_default_filename = "stellaris.exe" # Game executable name plus extension
        self.exe_out_directory = os.path.abspath(get_current_dir()) # Where to place the patched executable.
        self.exe_modified_filename = "stellaris-patched" # Name of modified executable
        self.is_patched = False
        
        self._steam = steam_helper.SteamHelper()

        if self._dev: # Change certain values if running from executable or IDE/Console. Development purposes.
            self.exe_out_directory = os.path.abspath(os.path.join(get_current_dir(), os.pardir))

    # =============================================
    # ============== Class Functions ==============
    # =============================================

    @staticmethod
    def _generate_missing_paths(dir_path) -> None:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
    def compile_hex_file(self, directory=None, filename=None):
        if not directory:
            directory = self.exe_out_directory
        else:
            self.exe_out_directory = directory
        
        if not filename:
            filename = self.exe_modified_filename
        else:
            self.exe_modified_filename = filename
            
        dest = os.path.join(directory, f"{filename}.exe")
        
        if directory:
            self._generate_missing_paths(directory)
        else:
            self._generate_missing_paths(get_current_dir())
            
        with open(dest, "wb") as out:
            for line in self._hex_data_list_working:
                chunk = binascii.unhexlify(str(line).rstrip())
                out.write(chunk)
            logger.info(f"Writing {filename}.exe to: {directory}")
            
        return True
            
    def _convert_to_two_space(self, condense_chunks=False) -> list:
        # https://stackoverflow.com/a/10070449
        
        """
        Convert current loaded hex chunk to a list of two elements per item: From "XXXXXXXX" to ["XX", "XX", "XX", "XX", ..]
        
        This will output a list of lists [["XX", "XX", "XX", "XX", ..], ["XX", "XX", "XX", "XX", ..], ...]

        Condensing chunks joins all chunk lists into a single chunk list. From [["XX", "XX", "XX", "XX", ..], ["XX", "XX", "XX", "XX", ..], ...] to ["XX", "XX", "XX", "XX", "XX", "XX", "XX", "XX", ..]
        """
        
        logger.debug("Formatting hexadecimal data to working set...")
        
        formatted_hex_data_list = []
        
        for chunk in self.hex_data_list:
            converted = " ".join(chunk[i:i+2] for i in range(0,len(chunk),2))
            formatted_hex_data_list.append(converted)
            
        if condense_chunks:
            logger.debug("Condensing chunks...") # Here we take the list of chunks [["XX", "XX", "XX",..], ["XX", "XX", "XX", "XX",..]] and turn all into a single chunk -> ["XX, XX, XX, XX, XX,.."]
            self._hex_data_list_working.append(" ".join(formatted_hex_data_list))
        else:
            self._hex_data_list_working = formatted_hex_data_list
        
        return self._hex_data_list_working
    
    def _convert_hex_list_to_writable_chunk_list(self, hex_chunk_set: list) -> list:
        out_list = []
        
        tmp_chunk = []
        hex_iter = 0
        for hex_char in hex_chunk_set:
            if hex_iter < self._chunk_char_len/2:
                tmp_chunk.append(hex_char)
            else:
                out_list.append("".join(tmp_chunk))
                tmp_chunk.clear()
                hex_iter = 0
                tmp_chunk .append(hex_char)
                
            hex_iter += 1
        
        return out_list
            
    def _acquire_checksum_block(self) -> bool:
        logger.info("Acquiring Checksum Block...")
        
        working_set_hex = self._convert_to_two_space(condense_chunks=True)
        
        potential_candidate = False
        
        for chunk in working_set_hex:
            chunk_split = chunk.split(" ")
            # logger.log_debug(f"Chunk: {chunk}")
            # logger.log_debug(f"Chunk Split: {chunk_split}")
            for index, hex_char in enumerate(chunk_split):
                # CHECK FOR START SEQUENCE
                if hex_char in self._hex_begin_static and hex_char == self._hex_begin_static[0]:
                    # logger.log_debug(f"Found matching starting hex <{hex_char}> at index {index}")
                    start_candidate = []
                    start_sequence_len = len(self._hex_begin_static)
                    
                    for i in range(start_sequence_len):
                        start_candidate.append(chunk_split[index+i])
                    if start_candidate == self._hex_begin_static:
                        # logger.log_debug(f"Found potential start candidate: {start_candidate} starting from {index}")
                        
                        # CHECK FOR END SEQUENCE AFTER X WILDCARDS IN BETWEEN
                        # logger.log_debug("Checking for end sequence")
                        end_sequence_candidate = []
                        end_sequence_len = len(self._hex_end_static)
                        
                        # [start_index_chars, start_index_chars+1, start_index_chars+2, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, end_hex_char, end_hex_char+1]
                        # [48, 8B, 12, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, ??, 85, C0]
                        search_offset_start = index + start_sequence_len + self._hex_wildcards_in_between
                        # logger.log_debug(f"Search Offset Start {search_offset_start}")
                        for end_candidate in chunk_split[search_offset_start:search_offset_start + end_sequence_len]:
                            end_sequence_candidate.append(end_candidate)
                        
                        # logger.log_debug(f"End Candidate: {end_sequence_candidate}")
                        
                        if end_sequence_candidate == self._hex_end_static:
                            logger.debug(f"Found potential start candidate: {start_candidate} starting from {index}")
                            logger.debug(f"Found potential end candidate: {end_sequence_candidate} ending at index {search_offset_start + end_sequence_len}")
                            logger.debug(f"Search Offset Start: {search_offset_start - index}")
                            self._checksum_block = [hex_chunk for hex_chunk in chunk_split[index:search_offset_start + end_sequence_len]]
                            self._checksum_offset_start = index
                            self._checksum_offset_end = search_offset_start + end_sequence_len
                            logger.info(f"Found potential matching sequence.")
                            logger.debug(f"({index}) {''.join(self._checksum_block)} ({search_offset_start + self._checksum_offset_end})")
                            potential_candidate = True
                            break
                        elif end_sequence_candidate == self._hex_end_change_to:
                            logger.debug(f"Found potential start candidate: {start_candidate} starting from {index}")
                            logger.debug(f"Found potential patched end candidate: {end_sequence_candidate} ending at index {search_offset_start + end_sequence_len}")
                            # logger.log("Current executable is already patched and will not be touched further.")
                            self.is_patched = True
                            return False
        
        if potential_candidate:
            return True
        
        return False

    def _modify_checksum(self):
        logger.info("Patching Block...")
        if not self._checksum_block:
            return False
        
        checksum_block_modified = []
        for enum, hex_char in enumerate(self._checksum_block):
            if enum >= len(self._checksum_block) - len(self._hex_end_change_to):
                checksum_block_modified.extend(self._hex_end_change_to)
                break
            else:
                checksum_block_modified.append(hex_char)
                
        logger.debug(f"Original Block:  {''.join(self._checksum_block)}")
        logger.debug(f"Modified Block: {''.join(checksum_block_modified)}")

        if not self._hex_data_list_working:
            return False
        chunk_split = []
        for chunk in self._hex_data_list_working:
            chunk_split = chunk.split(" ")
            for offset, modify_hex in enumerate(checksum_block_modified):
                chunk_split[self._checksum_offset_start+offset] = modify_hex
    
        self._hex_data_list_working = self._convert_hex_list_to_writable_chunk_list(chunk_split)
        
        return True
    
    # ===============================================
    # ============== Regular Functions ==============
    # ===============================================
        
    def clear_caches(self):
        self._hex_data_list_working.clear()
        self._checksum_block.clear()
        self._checksum_offset_start = 0
        self._checksum_offset_end = 0
        self.is_patched = False
        
    def locate_game_install(self) -> Union[str, None]:
        """
        Returns path to game executable.
        """
        logger.info("Locating game install...")
        stellaris_install_path = self._steam.get_game_install_path(self.title_name)
        
        if stellaris_install_path:
            game_executable = os.path.join(stellaris_install_path, self.exe_default_filename)
            if not os.path.exists(game_executable):
                return None
            return game_executable
        
        return None
    
    def load_file_hex(self, file_path=None) -> bool:
        logger.info("Loading file Hex.")
        
        file_path = str(file_path).replace('/', '\\')
        
        if not file_path:
            file_path = os.path.join(self._base_dir, self.exe_default_filename)
                
            if not os.path.isfile(file_path):
                logger.error(f"Unable to find required file: {file_path}")
                return False
        
        self.hex_data_list.clear()
        
        if not os.path.exists(file_path):
            logger.error(f"{file_path} does not exist.")
            return False
        
        with open(file_path, "rb") as f:
            logger.info("Streaming File Hex Info...")
            while True:
                hex_data = f.read(16).hex()
                if len(hex_data) == 0:
                    break
                self.hex_data_list.append(hex_data.upper())

        self.data_loaded = True
        logger.info("Read Finished.")
        
        return True
    
    def write_hex_to_file(self, directory, filename, working_set=False):
        dest = os.path.join(directory, f"{filename}.txt")
        
        self._generate_missing_paths(directory)
        
        to_write = self.hex_data_list
        
        if working_set:
            to_write = self._hex_data_list_working
        
        with open(dest, 'w') as f:
            for chunk in to_write:
                f.write(chunk + '\n')
        
    def patch(self) -> bool:
        """
        Perform all necessary actions in bulk to patch the executable.

        :return:
        """

        self.clear_caches()
        
        if not self.data_loaded:
            op_success = False
        else:
            op_success = True

        # Each op_success will refer to the previous operation, therefore, when giving checking if-else
        # The else will refer to the error of the previous operation.

        if op_success: # Data was loaded.
            op_success = self._acquire_checksum_block()
            
            if op_success: # Checksum block was acquired.
                op_success = self._modify_checksum()
            
            if op_success: # Checksum block was modified.
                op_success = self.compile_hex_file()
        else: # Data was not loaded.
            logger.error("Unable to load data.")
            return False
        
        if op_success: # Patched exe file was generated.
            print("\n")
            logger.info(f"Patch successful.".upper())
            return True
        else: # Patched exe file was not generated.
            print("\n")
            # Here we could have failed because the file was already patched
            if self.is_patched:
                logger.info(f"Executable already patched.".upper())
            else:
                logger.error(f"Patch failed.".upper())
    
        return False
        
    