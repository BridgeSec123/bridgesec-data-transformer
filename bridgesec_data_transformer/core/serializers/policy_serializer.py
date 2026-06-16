import uuid
from datetime import datetime, timezone

from rest_framework import serializers

from core.services import rego_builder


class PolicyRuleSerializer(serializers.Serializer):
    """Serializer for PolicyRule (Supabase-backed).

    `rego_source`, `policy_id`, `created_by`, `created_at`, `updated_at` are
    server-managed — never accepted from the client.
    """

    policy_id   = serializers.CharField(read_only=True)
    name        = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    role        = serializers.CharField()
    entity      = serializers.CharField()
    action      = serializers.CharField()
    effect      = serializers.ChoiceField(choices=["allow", "deny"], default="allow")
    conditions  = serializers.DictField(required=False, default=dict)
    tenant_id   = serializers.CharField(allow_null=True, required=False, default=None)
    rego_source = serializers.CharField(read_only=True)
    created_by  = serializers.CharField(read_only=True)
    created_at  = serializers.CharField(read_only=True)
    updated_at  = serializers.CharField(read_only=True)

    def validate_conditions(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("conditions must be a JSON object.")

        allowed_keys = {
            "own_records_only",
            "exclude_actions",
            "field_conditions",
            "record_id_filter",
        }
        unknown = set(value.keys()) - allowed_keys
        if unknown:
            raise serializers.ValidationError(
                f"Unknown condition keys: {sorted(unknown)}. Allowed: {sorted(allowed_keys)}."
            )
        if "exclude_actions" in value and not isinstance(value["exclude_actions"], list):
            raise serializers.ValidationError("exclude_actions must be a list of strings.")
        if "field_conditions" in value and not isinstance(value["field_conditions"], dict):
            raise serializers.ValidationError("field_conditions must be a JSON object.")
        if "record_id_filter" in value and not isinstance(value["record_id_filter"], list):
            raise serializers.ValidationError("record_id_filter must be a list of strings.")
        if "own_records_only" in value and not isinstance(value["own_records_only"], bool):
            raise serializers.ValidationError("own_records_only must be a boolean.")
        return value

    def create(self, validated_data, tenant_id=None):
        from core.utils.supabase_policy import SupabasePolicyRule

        tenant_id = validated_data.pop("tenant_id", tenant_id)
        request = self.context.get("request")
        created_by = getattr(getattr(request, "user", None), "email", None) if request else None
        now = datetime.now(timezone.utc).isoformat()
        policy_id = str(uuid.uuid4())

        import types
        rule_ns = types.SimpleNamespace(
            policy_id=policy_id,
            tenant_id=tenant_id,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            **validated_data,
        )
        rego_text = rego_builder.translate(rule_ns)

        row = SupabasePolicyRule.create({
            "id":          policy_id,
            "name":        validated_data.get("name", ""),
            "description": validated_data.get("description", ""),
            "role":        validated_data["role"],
            "entity":      validated_data["entity"],
            "action":      validated_data["action"],
            "effect":      validated_data.get("effect", "allow"),
            "conditions":  validated_data.get("conditions") or {},
            "rego_source": rego_text,
            "tenant_id":   tenant_id,
            "created_by":  created_by,
            "created_at":  now,
            "updated_at":  now,
        })
        return row

    def update(self, instance, validated_data):
        from core.utils.supabase_policy import SupabasePolicyRule

        import types
        rule_ns = types.SimpleNamespace(
            policy_id=instance.id,
            **{k: validated_data.get(k, getattr(instance, k, None)) for k in
               ["role", "entity", "action", "effect", "conditions", "name", "description"]},
        )
        rego_text = rego_builder.translate(rule_ns)

        now = datetime.now(timezone.utc).isoformat()
        update_data = {**validated_data, "rego_source": rego_text, "updated_at": now}
        updated = SupabasePolicyRule.update(str(instance.id), update_data)
        return updated or instance

    def to_representation(self, instance):
        return {
            "policy_id":   instance.id,
            "name":        getattr(instance, "name", "") or "",
            "description": getattr(instance, "description", "") or "",
            "role":        instance.role,
            "entity":      instance.entity,
            "action":      instance.action,
            "effect":      instance.effect,
            "conditions":  instance.conditions or {},
            "rego_source": instance.rego_source,
            "tenant_id":   getattr(instance, "tenant_id", None),
            "created_by":  instance.created_by,
            "created_at":  instance.created_at,
            "updated_at":  instance.updated_at,
        }
