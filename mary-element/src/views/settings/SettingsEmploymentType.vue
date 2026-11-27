<template>
  <GenericSettingsView
    title="Employment Types"
    entityName="Employment Type"
    apiEndpoint="/employment-types"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
