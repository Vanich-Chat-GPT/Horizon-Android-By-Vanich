package dev.nova.horizon.account

import android.app.Activity
import android.content.Context
import com.microsoft.identity.client.AcquireTokenParameters
import com.microsoft.identity.client.AcquireTokenSilentParameters
import com.microsoft.identity.client.AuthenticationCallback
import com.microsoft.identity.client.IAccount
import com.microsoft.identity.client.IAuthenticationResult
import com.microsoft.identity.client.IMultipleAccountPublicClientApplication
import com.microsoft.identity.client.IPublicClientApplication
import com.microsoft.identity.client.PublicClientApplication
import com.microsoft.identity.client.exception.MsalException
import dev.nova.horizon.BuildConfig
import dev.nova.horizon.R

/** MSAL public-client adapter. No client secret is embedded in the Android app. */
internal object MicrosoftAuthManager {
    private val scopes = listOf("XboxLive.signin", "offline_access")

    @Volatile
    private var application: IMultipleAccountPublicClientApplication? = null

    @Volatile
    private var initializationInProgress = false

    fun isConfigured(): Boolean =
        BuildConfig.MICROSOFT_AUTH_CONFIGURED &&
            BuildConfig.MICROSOFT_CLIENT_ID.isNotBlank() &&
            BuildConfig.MICROSOFT_REDIRECT_SIGNATURE_HASH.isNotBlank()

    fun initialize(context: Context, callback: (Result<Unit>) -> Unit) {
        if (!isConfigured()) {
            callback(Result.failure(
                IllegalStateException(
                    "Microsoft OAuth ещё не настроен: отсутствуют MICROSOFT_CLIENT_ID и MICROSOFT_REDIRECT_SIGNATURE_HASH."
                )
            ))
            return
        }

        application?.let {
            callback(Result.success(Unit))
            return
        }
        synchronized(this) {
            application?.let {
                callback(Result.success(Unit))
                return
            }
            if (initializationInProgress) {
                callback(Result.failure(
                    IllegalStateException("Инициализация Microsoft OAuth уже выполняется. Повторите попытку через секунду.")
                ))
                return
            }
            initializationInProgress = true
        }

        PublicClientApplication.createMultipleAccountPublicClientApplication(
            context.applicationContext,
            R.raw.msal_config,
            object : IPublicClientApplication.IMultipleAccountApplicationCreatedListener {
                override fun onCreated(application: IMultipleAccountPublicClientApplication) {
                    this@MicrosoftAuthManager.application = application
                    synchronized(this@MicrosoftAuthManager) {
                        initializationInProgress = false
                    }
                    callback(Result.success(Unit))
                }

                override fun onError(exception: MsalException) {
                    synchronized(this@MicrosoftAuthManager) {
                        initializationInProgress = false
                    }
                    callback(Result.failure(exception))
                }
            }
        )
    }

    fun acquireToken(activity: Activity, callback: (Result<String>) -> Unit) {
        val current = application
        if (current == null) {
            callback(Result.failure(IllegalStateException("Microsoft OAuth не инициализирован.")))
            return
        }

        val parameters = AcquireTokenParameters.Builder()
            .withScopes(scopes)
            .startAuthorizationFromActivity(activity)
            .withCallback(object : AuthenticationCallback {
                override fun onSuccess(authenticationResult: IAuthenticationResult) {
                    val token = authenticationResult.accessToken
                    if (token.isBlank()) {
                        callback(Result.failure(IllegalStateException("Microsoft не вернул access token.")))
                    } else {
                        callback(Result.success(token))
                    }
                }

                override fun onError(exception: MsalException) {
                    callback(Result.failure(exception))
                }

                override fun onCancel() {
                    callback(Result.failure(IllegalStateException("Вход Microsoft отменён.")))
                }
            })
            .build()

        current.acquireToken(parameters)
    }

    fun acquireTokenSilently(callback: (Result<String>) -> Unit) {
        val current = application
        if (current == null) {
            callback(Result.failure(IllegalStateException("Microsoft OAuth не инициализирован.")))
            return
        }

        current.getAccounts(object : IPublicClientApplication.LoadAccountsCallback {
            override fun onTaskCompleted(accounts: List<IAccount>) {
                val account = accounts.firstOrNull()
                if (account == null) {
                    callback(Result.failure(IllegalStateException("В Microsoft ещё нет подключённого аккаунта.")))
                    return
                }

                val parameters = AcquireTokenSilentParameters.Builder()
                    .withScopes(scopes)
                    .forAccount(account)
                    .fromAuthority(account.authority)
                    .withCallback(object : AuthenticationCallback {
                        override fun onSuccess(authenticationResult: IAuthenticationResult) {
                            val token = authenticationResult.accessToken
                            if (token.isBlank()) {
                                callback(Result.failure(IllegalStateException("Microsoft не вернул access token.")))
                            } else {
                                callback(Result.success(token))
                            }
                        }

                        override fun onError(exception: MsalException) {
                            callback(Result.failure(exception))
                        }

                        override fun onCancel() {
                            callback(Result.failure(IllegalStateException("Тихое обновление Microsoft отменено.")))
                        }
                    })
                    .build()
                current.acquireTokenSilentAsync(parameters)
            }

            override fun onError(exception: MsalException) {
                callback(Result.failure(exception))
            }
        })
    }

    fun signOut(context: Context, callback: (Result<Unit>) -> Unit) {
        initialize(context) { initialized ->
            initialized.fold(
                onSuccess = {
                    val current = application
                    if (current == null) {
                        callback(Result.failure(IllegalStateException("Microsoft OAuth недоступен.")))
                    } else {
                        current.getAccounts(object : IPublicClientApplication.LoadAccountsCallback {
                            override fun onTaskCompleted(accounts: List<IAccount>) {
                                val account = accounts.firstOrNull()
                                if (account == null) {
                                    callback(Result.success(Unit))
                                    return
                                }
                                current.removeAccount(
                                    account,
                                    object : IMultipleAccountPublicClientApplication.RemoveAccountCallback {
                                        override fun onRemoved() {
                                            callback(Result.success(Unit))
                                        }

                                        override fun onError(exception: MsalException) {
                                            callback(Result.failure(exception))
                                        }
                                    }
                                )
                            }

                            override fun onError(exception: MsalException) {
                                callback(Result.failure(exception))
                            }
                        })
                    }
                },
                onFailure = { failure -> callback(Result.failure(failure)) }
            )
        }
    }
}
