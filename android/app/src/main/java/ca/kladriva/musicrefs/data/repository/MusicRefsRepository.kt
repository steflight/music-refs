package ca.kladriva.musicrefs.data.repository

import ca.kladriva.musicrefs.data.api.ApiResult
import ca.kladriva.musicrefs.data.api.MusicRefsApi
import ca.kladriva.musicrefs.data.api.safeApi
import ca.kladriva.musicrefs.data.model.CategoryDto
import ca.kladriva.musicrefs.data.model.GameMode
import ca.kladriva.musicrefs.data.model.PartyCreateRequest
import ca.kladriva.musicrefs.data.model.PartyJoinRequest
import ca.kladriva.musicrefs.data.model.PartyScoreRequest
import ca.kladriva.musicrefs.data.model.PartySnapshotDto
import ca.kladriva.musicrefs.data.model.PartyStartRequest
import ca.kladriva.musicrefs.domain.game.Quote
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MusicRefsRepository @Inject constructor(
    private val api: MusicRefsApi,
) {
    suspend fun categories(): ApiResult<List<CategoryDto>> = safeApi { api.categories() }

    suspend fun quotes(categoryId: Int?): ApiResult<List<Quote>> = safeApi {
        api.quotes(categoryId).map { it.toDomain() }
    }

    suspend fun createParty(
        categoryId: Int,
        hostName: String,
        roundLimit: Int,
        mode: GameMode,
    ): ApiResult<PartySnapshotDto> = safeApi {
        api.createParty(
            PartyCreateRequest(
                categoryId = categoryId,
                hostName = hostName,
                roundLimit = roundLimit,
                mode = mode.apiValue,
            ),
        )
    }

    suspend fun joinParty(code: String, playerName: String): ApiResult<PartySnapshotDto> = safeApi {
        api.joinParty(PartyJoinRequest(code = code.trim().uppercase(), playerName = playerName))
    }

    suspend fun party(code: String): ApiResult<PartySnapshotDto> = safeApi { api.party(code) }

    suspend fun startParty(code: String, hostToken: String): ApiResult<PartySnapshotDto> = safeApi {
        api.startParty(code, PartyStartRequest(hostToken))
    }

    suspend fun partyQuotes(code: String): ApiResult<List<Quote>> = safeApi {
        api.partyQuotes(code).map { it.toDomain() }
    }

    suspend fun updateScore(
        code: String,
        playerToken: String,
        score: Int,
        finished: Boolean,
        progress: Int?,
    ): ApiResult<PartySnapshotDto> = safeApi {
        api.updateScore(
            code,
            PartyScoreRequest(
                playerToken = playerToken,
                score = score,
                finished = finished,
                progress = progress,
            ),
        )
    }
}
