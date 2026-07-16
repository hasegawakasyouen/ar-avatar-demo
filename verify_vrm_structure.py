# verify_vrm_structure.py
import struct
import json

with open(r"C:\Users\PC_User\Documents\ar-avatar-demo\model.vrm", "rb") as f:
    data = f.read()

magic, version, length = struct.unpack('<4sII', data[0:12])
assert magic == b'glTF', f"glTFマジックナンバーが不正: {magic}"

offset = 12
chunk_length, chunk_type = struct.unpack('<II', data[offset:offset + 8])
offset += 8
json_data = data[offset:offset + chunk_length]
gltf = json.loads(json_data)

extensions = gltf.get("extensions", {})
assert "VRMC_vrm" in extensions, "VRMC_vrm拡張が見つかりません"
humanoid = extensions["VRMC_vrm"]["humanoid"]["humanBones"]
assert "hips" in humanoid, "hipsボーンがVRM内に見つかりません"
expressions = extensions["VRMC_vrm"].get("expressions", {})
print("PRESET_EXPRESSIONS:", list(expressions.get("preset", {}).keys()))
print("CUSTOM_EXPRESSIONS:", list(expressions.get("custom", {}).keys()))
print("VRM_STRUCTURE_OK")
