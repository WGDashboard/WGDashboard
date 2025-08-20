<script setup lang="ts">
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js"
const props = defineProps(["BackgroundColor", "GroupName", "Icon"])
const store = WireguardConfigurationsStore();
</script>

<template>
<h6 class="mb-0">
	<span
		class="badge rounded-3 shadow"
		:style="{'background-color': BackgroundColor, 'color': store.colorText(BackgroundColor) }"
	>
	<i class="bi" :class="[Icon, GroupName ? 'me-2': '']" v-if="Icon"></i>{{ GroupName }}
</span>
</h6>
</template>

<style scoped>

</style>