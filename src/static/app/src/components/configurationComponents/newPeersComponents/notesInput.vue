<script>
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "notesInput",
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
		<label for="peer_notes_textbox" class="form-label">
			<small class="text-muted">
				<LocaleText t="Notes"></LocaleText>
			</small>
		</label>
		<input type="text" class="form-control form-control-sm rounded-3"
		       :disabled="this.saving || this.bulk"
		       v-model="this.data.notes"
		       id="peer_notes_textbox" placeholder="">
	</div>
</template>

<style scoped>

</style>