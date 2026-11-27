<template>
  <GenericSettingsView
    title="General Practitioner (GP) Practices"
    entityName="GP Practice"
    apiEndpoint="/gps"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
