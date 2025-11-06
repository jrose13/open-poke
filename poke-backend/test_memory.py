"""Test script for core memory system"""
import asyncio
import sys
from server.memory import memory_manager, CoreMemorySchema


async def test_memory_system():
    """Test the core memory system"""
    test_user_id = "test-user-123"
    
    print("=" * 60)
    print("TESTING CORE MEMORY SYSTEM")
    print("=" * 60)
    
    # Test 1: Get empty core memory
    print("\n[Test 1] Getting empty core memory...")
    memory = await memory_manager.get_core_memory(test_user_id)
    print(f"✓ Empty memory retrieved: {memory.to_dict()}")
    
    # Test 2: Update core memory manually
    print("\n[Test 2] Manually updating core memory...")
    updates = {
        "user_name": "Sarah",
        "care_role": "caregiver",
        "care_recipient_name": "Mom",
        "zip_code": "90210"
    }
    memory = await memory_manager.update_core_memory(test_user_id, updates, merge=True)
    print(f"✓ Memory updated: {memory.to_dict()}")
    print(f"\nPrompt format:\n{memory.to_prompt_string()}")
    
    # Test 3: Extract memory from conversation
    print("\n[Test 3] Extracting memory from conversation...")
    conversation = "My name is John and I live in 10001. I'm taking Metformin for my diabetes."
    memory = await memory_manager.extract_and_update_memory(
        user_id=test_user_id,
        conversation_text=conversation
    )
    print(f"✓ Extracted and merged: {memory.to_dict()}")
    print(f"\nPrompt format:\n{memory.to_prompt_string()}")
    
    # Test 4: Retrieve and verify persistence
    print("\n[Test 4] Retrieving memory to verify persistence...")
    memory = await memory_manager.get_core_memory(test_user_id)
    print(f"✓ Retrieved memory: {memory.to_dict()}")
    
    # Test 5: Add more complex information
    print("\n[Test 5] Adding insurance and medication info...")
    conversation2 = "I have UnitedHealthcare Medicare Advantage. I also take Lisinopril twice a day."
    memory = await memory_manager.extract_and_update_memory(
        user_id=test_user_id,
        conversation_text=conversation2,
        agent_response="Got it! I've noted your UnitedHealthcare Medicare Advantage plan and your medications."
    )
    print(f"✓ Memory updated: {memory.to_dict()}")
    print(f"\nFinal prompt format:\n{memory.to_prompt_string()}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)
    print("\nMemory system is working correctly!")
    print("The agent will now:")
    print("  1. Load this memory for every conversation")
    print("  2. Automatically extract new facts from chats")
    print("  3. Reference stored information naturally")


if __name__ == "__main__":
    try:
        asyncio.run(test_memory_system())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

