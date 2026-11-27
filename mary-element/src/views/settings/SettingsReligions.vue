<template>
  <GenericSettingsView
    title="Religions & Faith Orientations"
    entityName="Religion"
    apiEndpoint="/religions"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
