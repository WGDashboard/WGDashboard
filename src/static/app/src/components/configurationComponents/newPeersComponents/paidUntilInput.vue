<script>
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "paidUntilInput",
	components: {LocaleText},
	props: {
		bulk: Boolean,
		data: Object,
		saving: Boolean
	}
}
</script>

<template>
	<div :class="{inactiveField: this.bulk}">
		<label for="peer_paid_until_textbox" class="form-label">
			<small class="text-muted">
				<LocaleText t="Paid Until"></LocaleText>
			</small>
		</label>
		<input type="date" class="form-control form-control-sm rounded-3"
		       :disabled="this.saving || this.bulk || this.data.paid_unlimited"
		       v-model="this.data.paid_until"
		       id="peer_paid_until_textbox">
		<div class="form-check form-switch mt-2">
			<input class="form-check-input" type="checkbox" role="switch"
			       v-model="this.data.paid_unlimited"
			       :disabled="this.saving || this.bulk"
			       id="peer_paid_unlimited_switch">
			<label class="form-check-label" for="peer_paid_unlimited_switch">
				<small class="fw-bold">
					<LocaleText t="Unlimited"></LocaleText>
				</small>
				<div class="form-text">
					<LocaleText t="The peer is always considered paid, without an end date"></LocaleText>
				</div>
			</label>
		</div>
	</div>
</template>

<style scoped>

</style>
