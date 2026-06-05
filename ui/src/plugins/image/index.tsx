import type { RenderActionResultProps, RenderFetcherResultProps } from '../ClueUIPlugin';
import ClueUIPlugin from '../ClueUIPlugin';

class ImagePlugin extends ClueUIPlugin {
  name = 'ImagePlugin';
  format = 'image';
  version = '1.0.0';
  author = 'Mr. Green';
  description = 'Renders images.';

  actionResult(props: RenderActionResultProps) {
    const { result, setShowPreview, ...additionalProps } = props;
    return (
      <img
        src={result.output.image}
        alt={result.output.alt}
        {...additionalProps}
        onClick={() => setShowPreview?.(true)}
      />
    );
  }

  fetcherResult(props: RenderFetcherResultProps) {
    const { result, setShowPreview, ...additionalProps } = props;
    return (
      <img src={result.data.image} alt={result.data.alt} {...additionalProps} onClick={() => setShowPreview?.(true)} />
    );
  }
}
export default ImagePlugin;
