package dev.nova.horizon.account

import android.content.Context

internal data class MinecraftAccountStatus(
    val profileId: String?,
    val profileName: String?,
    val entitlementVerifiedAtMillis: Long?,
    val hasJavaEntitlement: Boolean
) {
    val isSignedIn: Boolean get() = !profileId.isNullOrBlank() && !profileName.isNullOrBlank()
}

internal object MinecraftAccountStore {
    private const val PREFS = "nova_account_status_v1"
    private const val KEY_PROFILE_ID = "profile_id"
    private const val KEY_PROFILE_NAME = "profile_name"
    private const val KEY_ENTITLEMENT_AT = "entitlement_verified_at"

    private const val ENTITLEMENT_MAX_AGE_MS = 24L * 60L * 60L * 1000L

    fun read(context: Context): MinecraftAccountStatus {
        val values = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val profileId = values.getString(KEY_PROFILE_ID, null)
        val profileName = values.getString(KEY_PROFILE_NAME, null)
        val verifiedAt = if (values.contains(KEY_ENTITLEMENT_AT)) {
            values.getLong(KEY_ENTITLEMENT_AT, 0L)
        } else {
            null
        }
        return MinecraftAccountStatus(
            profileId = profileId,
            profileName = profileName,
            entitlementVerifiedAtMillis = verifiedAt,
            hasJavaEntitlement = verifiedAt != null &&
                verifiedAt <= System.currentTimeMillis() &&
                System.currentTimeMillis() - verifiedAt <= ENTITLEMENT_MAX_AGE_MS &&
                !profileId.isNullOrBlank() && !profileName.isNullOrBlank()
        )
    }

    /**
     * Called only after the authenticated Minecraft Services profile and entitlement
     * response have both been verified. No UI toggle can grant entitlement.
     */
    fun saveVerifiedProfile(
        context: Context,
        profileId: String,
        profileName: String,
        entitlementVerifiedAtMillis: Long
    ) {
        require(profileId.matches(Regex("^[0-9a-fA-F-]{32,36}$")))
        require(profileName.isNotBlank() && profileName.length <= 64)
        require(entitlementVerifiedAtMillis > 0L)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_PROFILE_ID, profileId)
            .putString(KEY_PROFILE_NAME, profileName)
            .putLong(KEY_ENTITLEMENT_AT, entitlementVerifiedAtMillis)
            .apply()
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }
}
