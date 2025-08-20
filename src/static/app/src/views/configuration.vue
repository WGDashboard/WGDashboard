<script>
export default {
	name: "configuration",
}
</script>

<template>
	<div class="mt-md-5 mt-3 text-body">
		<RouterView v-slot="{ Component, route }">
			<Transition name="fade2" mode="out-in">
				<Suspense>
					<Component :is="Component" :key="route.path" class="z-1"></Component>
				</Suspense>
			</Transition>
		</RouterView>
	</div>
</template>

<style scoped>
	
</style>