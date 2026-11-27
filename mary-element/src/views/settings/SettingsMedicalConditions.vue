<template>
  <GenericSettingsView
    title="Medical Conditions Catalog"
    entityName="Medical Condition"
    apiEndpoint="/medical-conditions"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
