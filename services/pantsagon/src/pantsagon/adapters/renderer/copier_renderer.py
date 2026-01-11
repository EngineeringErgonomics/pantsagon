from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.ports.renderer import RenderOutcome, RenderRequest


class CopierRenderer:
    def render(self, request: RenderRequest) -> RenderOutcome:
        try:
            from copier import run_copy

            run_copy(
                str(request.pack_path),
                str(request.staging_dir),
                data=request.answers,
                skip_if_exists=("**/*",),
                unsafe=request.allow_hooks,
            )
        except Exception as e:  # Copier raises various exceptions
            raise RendererExecutionError(
                "Copier failed", details={"pack": request.pack.id}, cause=e
            )
        return RenderOutcome(rendered_paths=[request.staging_dir], warnings=[])
