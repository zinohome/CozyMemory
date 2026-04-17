#!/usr/bin/env python3
"""
Mem0 Memory Bug Fixes

This script applies fixes to mem0/memory/main.py to address several bugs:
1. KeyError when accessing temp_uuid_mapping with non-existent keys
2. KeyError when JSON response doesn't have "facts" key
3. AttributeError when vector_store.get returns None
4. Direct payload access that could cause KeyError

Usage:
    python apply_memory_fixes.py /path/to/mem0/memory/main.py
"""

import sys
import re
import os


def apply_fixes(file_path: str) -> bool:
    """Apply all memory fixes to the main.py file."""
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Fix 0: Ensure custom_fact_extraction_prompt includes "json" keyword
    # OpenAI requires "json" in the prompt when using response_format: json_object
    custom_prompt_old = '''        if self.config.custom_fact_extraction_prompt:
            system_prompt = self.config.custom_fact_extraction_prompt'''
    
    custom_prompt_new = '''        if self.config.custom_fact_extraction_prompt:
            # OpenAI requires "json" in the prompt when using response_format: json_object
            # Ensure the custom prompt includes "json" keyword
            if "json" not in self.config.custom_fact_extraction_prompt.lower():
                system_prompt = self.config.custom_fact_extraction_prompt + "\\n\\nPlease respond in JSON format with a 'facts' array."
            else:
                system_prompt = self.config.custom_fact_extraction_prompt'''
    
    count = content.count(custom_prompt_old)
    if count > 0:
        content = content.replace(custom_prompt_old, custom_prompt_new)
        fixes_applied += count
        print(f"✓ Fix 0: Added JSON keyword check to custom_fact_extraction_prompt ({count} occurrences)")
    
    # Fix 1: JSON parsing - use .get("facts", []) instead of ["facts"]
    # Pattern: json.loads(response)["facts"]
    pattern1 = r'json\.loads\(response\)\["facts"\]'
    replacement1 = 'json.loads(response).get("facts", [])'
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        fixes_applied += 1
        print("✓ Fix 1: Fixed json.loads(response)[\"facts\"] -> .get(\"facts\", [])")
    
    # Pattern: json.loads(extracted_json)["facts"]
    pattern2 = r'json\.loads\(extracted_json\)\["facts"\]'
    replacement2 = 'json.loads(extracted_json).get("facts", [])'
    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement2, content)
        fixes_applied += 1
        print("✓ Fix 2: Fixed json.loads(extracted_json)[\"facts\"] -> .get(\"facts\", [])")
    
    # Fix 2: Replace direct temp_uuid_mapping access in UPDATE (sync version)
    # This is more complex, need to find and replace the entire UPDATE block
    
    # Pattern for sync UPDATE block
    sync_update_old = '''                    elif event_type == "UPDATE":
                        self._update_memory(
                            memory_id=temp_uuid_mapping[resp.get("id")],
                            data=action_text,
                            existing_embeddings=new_message_embeddings,
                            metadata=deepcopy(metadata),
                        )
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp.get("id")],
                                "memory": action_text,
                                "event": event_type,
                                "previous_memory": resp.get("old_memory"),
                            }
                        )'''
    
    sync_update_new = '''                    elif event_type == "UPDATE":
                        # Check if the memory ID exists in the mapping
                        memory_id_to_update = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id_to_update is None:
                            # If memory doesn't exist, treat UPDATE as ADD
                            logger.warning(f"Memory ID '{resp.get('id')}' not found in existing memories, treating UPDATE as ADD")
                            memory_id = self._create_memory(
                                data=action_text,
                                existing_embeddings=new_message_embeddings,
                                metadata=deepcopy(metadata),
                            )
                            returned_memories.append({"id": memory_id, "memory": action_text, "event": "ADD"})
                        else:
                            self._update_memory(
                                memory_id=memory_id_to_update,
                                data=action_text,
                                existing_embeddings=new_message_embeddings,
                                metadata=deepcopy(metadata),
                            )
                            returned_memories.append(
                                {
                                    "id": memory_id_to_update,
                                    "memory": action_text,
                                    "event": event_type,
                                    "previous_memory": resp.get("old_memory"),
                                }
                            )'''
    
    if sync_update_old in content:
        content = content.replace(sync_update_old, sync_update_new)
        fixes_applied += 1
        print("✓ Fix 3: Fixed sync UPDATE block - added temp_uuid_mapping check")
    
    # Fix 3: Replace direct temp_uuid_mapping access in DELETE (sync version)
    sync_delete_old = '''                    elif event_type == "DELETE":
                        self._delete_memory(memory_id=temp_uuid_mapping[resp.get("id")])
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp.get("id")],
                                "memory": action_text,
                                "event": event_type,
                            }
                        )'''
    
    sync_delete_new = '''                    elif event_type == "DELETE":
                        # Check if the memory ID exists before deleting
                        memory_id_to_delete = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id_to_delete is None:
                            logger.warning(f"Memory ID '{resp.get('id')}' not found in existing memories, skipping DELETE")
                        else:
                            self._delete_memory(memory_id=memory_id_to_delete)
                            returned_memories.append(
                                {
                                    "id": memory_id_to_delete,
                                    "memory": action_text,
                                    "event": event_type,
                                }
                            )'''
    
    if sync_delete_old in content:
        content = content.replace(sync_delete_old, sync_delete_new)
        fixes_applied += 1
        print("✓ Fix 4: Fixed sync DELETE block - added temp_uuid_mapping check")
    
    # Fix 4: Add None check for vector_store.get in NONE event (sync version)
    sync_none_old = '''                    elif event_type == "NONE":
                        # Even if content doesn't need updating, update session IDs if provided
                        memory_id = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id and (metadata.get("agent_id") or metadata.get("run_id")):
                            # Update only the session identifiers, keep content the same
                            existing_memory = self.vector_store.get(vector_id=memory_id)
                            updated_metadata = deepcopy(existing_memory.payload)'''
    
    sync_none_new = '''                    elif event_type == "NONE":
                        # Even if content doesn't need updating, update session IDs if provided
                        memory_id = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id and (metadata.get("agent_id") or metadata.get("run_id")):
                            # Update only the session identifiers, keep content the same
                            existing_memory = self.vector_store.get(vector_id=memory_id)
                            if existing_memory is None:
                                logger.warning(f"Memory {memory_id} not found when trying to update session IDs")
                                continue
                            updated_metadata = deepcopy(existing_memory.payload)'''
    
    if sync_none_old in content:
        content = content.replace(sync_none_old, sync_none_new)
        fixes_applied += 1
        print("✓ Fix 5: Added None check for vector_store.get in sync NONE event")
    
    # Fix 5: Replace direct temp_uuid_mapping access in UPDATE (async version)
    async_update_old = '''                    elif event_type == "UPDATE":
                        task = asyncio.create_task(
                            self._update_memory(
                                memory_id=temp_uuid_mapping[resp["id"]],
                                data=action_text,
                                existing_embeddings=new_message_embeddings,
                                metadata=deepcopy(metadata),
                            )
                        )
                        memory_tasks.append((task, resp, "UPDATE", temp_uuid_mapping[resp["id"]]))'''
    
    async_update_new = '''                    elif event_type == "UPDATE":
                        # Check if the memory ID exists in the mapping
                        memory_id_to_update = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id_to_update is None:
                            # If memory doesn't exist, treat UPDATE as ADD
                            logger.warning(f"Memory ID '{resp.get('id')}' not found in existing memories, treating UPDATE as ADD (async)")
                            task = asyncio.create_task(
                                self._create_memory(
                                    data=action_text,
                                    existing_embeddings=new_message_embeddings,
                                    metadata=deepcopy(metadata),
                                )
                            )
                            memory_tasks.append((task, resp, "ADD", None))
                        else:
                            task = asyncio.create_task(
                                self._update_memory(
                                    memory_id=memory_id_to_update,
                                    data=action_text,
                                    existing_embeddings=new_message_embeddings,
                                    metadata=deepcopy(metadata),
                                )
                            )
                            memory_tasks.append((task, resp, "UPDATE", memory_id_to_update))'''
    
    if async_update_old in content:
        content = content.replace(async_update_old, async_update_new)
        fixes_applied += 1
        print("✓ Fix 6: Fixed async UPDATE block - added temp_uuid_mapping check")
    
    # Fix 6: Replace direct temp_uuid_mapping access in DELETE (async version)
    async_delete_old = '''                    elif event_type == "DELETE":
                        task = asyncio.create_task(self._delete_memory(memory_id=temp_uuid_mapping[resp.get("id")]))
                        memory_tasks.append((task, resp, "DELETE", temp_uuid_mapping[resp.get("id")]))'''
    
    async_delete_new = '''                    elif event_type == "DELETE":
                        # Check if the memory ID exists before deleting
                        memory_id_to_delete = temp_uuid_mapping.get(resp.get("id"))
                        if memory_id_to_delete is None:
                            logger.warning(f"Memory ID '{resp.get('id')}' not found in existing memories, skipping DELETE (async)")
                        else:
                            task = asyncio.create_task(self._delete_memory(memory_id=memory_id_to_delete))
                            memory_tasks.append((task, resp, "DELETE", memory_id_to_delete))'''
    
    if async_delete_old in content:
        content = content.replace(async_delete_old, async_delete_new)
        fixes_applied += 1
        print("✓ Fix 7: Fixed async DELETE block - added temp_uuid_mapping check")
    
    # Fix 7: Add None check for vector_store.get in async NONE event
    async_none_old = '''                            async def update_session_ids(mem_id, meta):
                                existing_memory = await asyncio.to_thread(self.vector_store.get, vector_id=mem_id)
                                updated_metadata = deepcopy(existing_memory.payload)'''
    
    async_none_new = '''                            async def update_session_ids(mem_id, meta):
                                existing_memory = await asyncio.to_thread(self.vector_store.get, vector_id=mem_id)
                                if existing_memory is None:
                                    logger.warning(f"Memory {mem_id} not found when trying to update session IDs (async)")
                                    return
                                updated_metadata = deepcopy(existing_memory.payload)'''
    
    if async_none_old in content:
        content = content.replace(async_none_old, async_none_new)
        fixes_applied += 1
        print("✓ Fix 8: Added None check for vector_store.get in async NONE event")
    
    # Fix 8: Replace direct payload access with .get() in _update_memory
    payload_fixes = [
        ('existing_memory.payload["user_id"]', 'existing_memory.payload.get("user_id")'),
        ('existing_memory.payload["agent_id"]', 'existing_memory.payload.get("agent_id")'),
        ('existing_memory.payload["run_id"]', 'existing_memory.payload.get("run_id")'),
        ('existing_memory.payload["actor_id"]', 'existing_memory.payload.get("actor_id")'),
        ('existing_memory.payload["role"]', 'existing_memory.payload.get("role")'),
    ]
    
    for old, new in payload_fixes:
        if old in content:
            content = content.replace(old, new)
            fixes_applied += 1
            print(f"✓ Fixed payload access: {old} -> {new}")
    
    # Check if any fixes were applied
    if content == original_content:
        print("WARNING: No fixes were applied. The file may already be patched or the patterns don't match.")
        return True
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Successfully applied {fixes_applied} fixes to {file_path}")
    return True


def main():
    if len(sys.argv) < 2:
        # Try to find the file automatically
        import subprocess
        try:
            result = subprocess.run(
                ['python3', '-c', 'import mem0.memory.main; import os; print(os.path.dirname(mem0.memory.main.__file__))'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                mem0_path = result.stdout.strip()
                file_path = os.path.join(mem0_path, 'main.py')
            else:
                print("ERROR: Could not find mem0 installation path")
                print("Usage: python apply_memory_fixes.py /path/to/mem0/memory/main.py")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            print("Usage: python apply_memory_fixes.py /path/to/mem0/memory/main.py")
            sys.exit(1)
    else:
        file_path = sys.argv[1]
    
    print(f"Applying Mem0 memory fixes to: {file_path}")
    print("=" * 60)
    
    success = apply_fixes(file_path)
    
    if success:
        print("\n" + "=" * 60)
        print("All fixes applied successfully!")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("ERROR: Failed to apply fixes")
        sys.exit(1)


if __name__ == "__main__":
    main()
